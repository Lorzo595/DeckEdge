using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using System.Xml;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace DeckEdgeDesktop
{
    internal static class Program
    {
        internal static string Project;
        internal static string DataDirectory;
        internal static string PhoneKey;
        internal static string PhoneHost;
        internal static bool PhoneDiscoveryReady;
        internal static string InstanceKey;
        internal static readonly object LogLock = new object();

        [STAThread]
        static void Main(string[] args)
        {
            string executableDirectory = AppDomain.CurrentDomain.BaseDirectory;
            bool packaged = File.Exists(Path.Combine(executableDirectory, "desktop_backend.py"));
            Project = packaged ? executableDirectory : Path.GetFullPath(Path.Combine(executableDirectory, "..", ".."));
            DataDirectory = !packaged ? Project : File.Exists(Path.Combine(Project, "portable.flag"))
                ? Path.Combine(Project, "data") : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "DeckEdge");
            string customData = Environment.GetEnvironmentVariable("DECKEDGE_DATA_DIR");
            if (!String.IsNullOrWhiteSpace(customData)) DataDirectory = Path.GetFullPath(customData);
            Directory.CreateDirectory(DataDirectory);
            string keyFile = Path.Combine(DataDirectory, ".phone-key");
            PhoneKey = File.Exists(keyFile) ? File.ReadAllText(keyFile).Trim() : "";
            if (!System.Text.RegularExpressions.Regex.IsMatch(PhoneKey, "^[a-f0-9]{64}$")) {
                var bytes = new byte[32];
                using (var random = RandomNumberGenerator.Create()) random.GetBytes(bytes);
                PhoneKey = BitConverter.ToString(bytes).Replace("-", "").ToLowerInvariant();
                File.WriteAllText(keyFile, PhoneKey, Encoding.ASCII);
            }
            if (args.Length == 3 && args[0] == "--sensors") {
                SensorWorker.Run(args[1], Int32.Parse(args[2])); return;
            }
            using (var sha = SHA256.Create())
                InstanceKey = "Local\\DeckEdge-" + BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(Project.ToLowerInvariant()))).Replace("-", "").Substring(0, 20);
            bool owner;
            using (var mutex = new Mutex(true, InstanceKey, out owner))
            using (var show = new EventWaitHandle(false, EventResetMode.AutoReset, InstanceKey + "-show"))
            using (var stop = new EventWaitHandle(false, EventResetMode.AutoReset, InstanceKey + "-stop"))
            {
                if (args.Contains("--quit")) { if (!owner) stop.Set(); return; }
                if (!owner) { show.Set(); return; }
                try
                {
                    Application.EnableVisualStyles();
                    Application.SetCompatibleTextRenderingDefault(false);
                    Application.Run(new StudioForm(show, stop, args.Contains("--background")));
                }
                catch (Exception ex)
                {
                    Log(ex.ToString());
                    MessageBox.Show("DeckEdge ne peut pas démarrer.\n\n" + ex.Message + "\n\nJournal : " + Path.Combine(DataDirectory, "desktop.log"), "DeckEdge", MessageBoxButtons.OK, MessageBoxIcon.Error);
                }
                finally { mutex.ReleaseMutex(); }
            }
        }

        internal static void Log(string message)
        {
            try { lock (LogLock) File.AppendAllText(Path.Combine(DataDirectory, "desktop.log"), DateTime.Now.ToString("s") + " " + message + Environment.NewLine, Encoding.UTF8); }
            catch { }
        }
    }

    public sealed class StudioForm : Form
    {
        const string AdminUrl = "http://127.0.0.1:5000/admin";
        const string HealthUrl = "http://127.0.0.1:5000/api/health";
        readonly WebView2 view = new WebView2();
        readonly Label message = new Label();
        readonly StatusStrip status = new StatusStrip();
        readonly ToolStripStatusLabel serverStatus = new ToolStripStatusLabel("Démarrage du serveur…");
        readonly ToolStripStatusLabel sensorStatus = new ToolStripStatusLabel("Capteurs en attente…");
        readonly NotifyIcon tray = new NotifyIcon();
        readonly System.Windows.Forms.Timer timer = new System.Windows.Forms.Timer();
        readonly EventWaitHandle showEvent, stopEvent;
        readonly ToolStripMenuItem keepAwake = new ToolStripMenuItem("Empêcher la mise en veille");
        readonly bool background;
        AppPreferences preferences;
        FormWindowState lastWindowState = FormWindowState.Normal;
        bool editorDirty;
        Process backend;
        StreamWriter backendInput;
        SensorBridge sensorBridge;
        readonly object backendInputLock = new object();
        bool quitting, cleaning, starting, polling, notified;
        string phoneUrl;

        [DllImport("kernel32.dll")] static extern uint SetThreadExecutionState(uint flags);
        [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr window);
        [DllImport("dwmapi.dll")] static extern int DwmSetWindowAttribute(IntPtr window, int attribute, ref int value, int size);

        public StudioForm(EventWaitHandle show, EventWaitHandle stop, bool startInBackground)
        {
            preferences = PreferencesStore.Load();
            showEvent = show; stopEvent = stop;
            background = startInBackground || (Environment.GetCommandLineArgs().Contains("--startup") && preferences.StartupInTray);
            Text = "DeckEdge — Studio";
            var screen = Screen.PrimaryScreen.WorkingArea;
            Size = new Size(Math.Max(860, Math.Min(preferences.WindowWidth, screen.Width)), Math.Max(600, Math.Min(preferences.WindowHeight, screen.Height)));
            MinimumSize = new Size(860, 600);
            if (preferences.WindowMaximized) { WindowState = FormWindowState.Maximized; lastWindowState = WindowState; }
            Resize += delegate { if (WindowState != FormWindowState.Minimized) lastWindowState = WindowState; };
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Color.FromArgb(23, 24, 23); ForeColor = Color.FromArgb(238, 238, 231);
            Font = new Font("Segoe UI", 10);
            Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
            view.Dock = DockStyle.Fill;
            view.DefaultBackgroundColor = BackColor;
            Controls.Add(view);
            message.Dock = DockStyle.Fill; message.TextAlign = ContentAlignment.MiddleCenter;
            message.Font = new Font("Segoe UI", 14); message.Padding = new Padding(40);
            message.Text = "DeckEdge\n\nPréparation du Studio et des capteurs…";
            Controls.Add(message); message.BringToFront();
            var retry = new Button { Text = "Réessayer", Dock = DockStyle.Bottom, Height = 42, FlatStyle = FlatStyle.Flat, Visible = false };
            retry.Click += async delegate { retry.Visible = false; await StartServices(); };
            retry.Name = "retry"; Controls.Add(retry);
            status.BackColor = Color.FromArgb(32, 34, 31); status.ForeColor = ForeColor;
            status.SizingGrip = false; status.Padding = new Padding(12, 5, 12, 5);
            serverStatus.Padding = new Padding(0, 0, 20, 0); sensorStatus.Spring = true; sensorStatus.TextAlign = ContentAlignment.MiddleLeft;
            phoneUrl = FindPhoneUrl();
            var copyPhone = new ToolStripButton("Connecter le téléphone");
            copyPhone.Click += delegate { OpenPhoneConnection(); };
            status.Items.AddRange(new ToolStripItem[] { serverStatus, sensorStatus, copyPhone });
            Controls.Add(status);
            var menu = new ContextMenuStrip();
            menu.Items.Add("Ouvrir le Studio", null, delegate { RestoreStudio(); });
            menu.Items.Add("Paramètres…", null, delegate { OpenSettings(); });
            menu.Items.Add("Connecter le téléphone (QR code)…", null, delegate { OpenPhoneConnection(); });
            menu.Items.Add("Copier le lien du téléphone", null, delegate { phoneUrl = FindPhoneUrl(); Clipboard.SetText(phoneUrl); });
            menu.Items.Add("Vérifier les capteurs", null, async delegate { await CheckSensors(); });
            if (File.Exists(Path.Combine(Program.Project, "prerequisites", "PawnIO_setup.exe")))
                menu.Items.Add("Installer l’accès matériel (PawnIO)…", null, async delegate { await InstallHardwareDriver(); });
            keepAwake.CheckOnClick = true; keepAwake.Checked = preferences.KeepAwake;
            keepAwake.CheckedChanged += delegate {
                preferences.KeepAwake = keepAwake.Checked; ApplyKeepAwake();
                try { PreferencesStore.Save(preferences, false); } catch (Exception ex) { Program.Log("Paramètres: " + ex.Message); }
            };
            menu.Items.Add(keepAwake);
            menu.Items.Add("Voir le journal", null, delegate { Process.Start(new ProcessStartInfo("notepad.exe", Quote(Path.Combine(Program.DataDirectory, "desktop.log"))) { UseShellExecute = true }); });
            menu.Items.Add("Ouvrir les données", null, delegate { Process.Start(new ProcessStartInfo("explorer.exe", Quote(Program.DataDirectory)) { UseShellExecute = true }); });
            menu.Items.Add(new ToolStripSeparator());
            menu.Items.Add("Quitter DeckEdge", null, delegate { RequestQuit(); });
            tray.Icon = Icon; tray.Text = "DeckEdge — démarrage"; tray.ContextMenuStrip = menu; tray.Visible = true;
            tray.DoubleClick += delegate { RestoreStudio(); };
            tray.BalloonTipClicked += delegate { RestoreStudio(); };
            timer.Interval = 1000;
            timer.Tick += async delegate {
                if (stopEvent.WaitOne(0)) { RequestQuit(); return; }
                if (showEvent.WaitOne(0)) RestoreStudio();
                if (!starting && !quitting) await RefreshHealth();
            };
            Shown += async delegate {
                int dark = 1; DwmSetWindowAttribute(Handle, 20, ref dark, sizeof(int));
                if (background) Hide();
                ApplyKeepAwake(); timer.Start(); await StartServices();
            };
            FormClosing += OnClosing;
            Microsoft.Win32.SystemEvents.SessionEnding += OnSessionEnding;
            Microsoft.Win32.SystemEvents.PowerModeChanged += OnPowerChanged;
        }

        static string Quote(string value) { return "\"" + value.Replace("\"", "") + "\""; }

        static string[] PhoneUrls()
        {
            return PhoneConnection.Addresses(Program.PhoneKey).Select(a => a.Url).ToArray();
        }

        static string FindPhoneUrl() { return PhoneUrls().FirstOrDefault() ?? "http://localhost:5000"; }

        void OpenPhoneConnection()
        {
            RestoreStudio();
            using (var dialog = new PhoneConnectionForm(async delegate {
                var health = await GetHealth();
                return health == null ? -1 : Convert.ToInt32(health["clients_connected"]);
            })) dialog.ShowDialog(this);
        }

        void ApplyKeepAwake() { SetThreadExecutionState(keepAwake.Checked ? 0x80000001u : 0x80000000u); }

        void RestoreStudio()
        {
            Show(); WindowState = lastWindowState; Activate(); SetForegroundWindow(Handle);
        }

        void SaveWindowPreferences()
        {
            Rectangle bounds = WindowState == FormWindowState.Normal ? Bounds : RestoreBounds;
            preferences.WindowWidth = bounds.Width; preferences.WindowHeight = bounds.Height;
            preferences.WindowMaximized = lastWindowState == FormWindowState.Maximized;
            try { PreferencesStore.Save(preferences, false); } catch (Exception ex) { Program.Log("Paramètres fenêtre: " + ex.Message); }
        }

        void OpenSettings()
        {
            RestoreStudio(); SaveWindowPreferences();
            preferences.StartWithWindows = PreferencesStore.StartupEnabled();
            using (var dialog = new SettingsForm(preferences)) {
                if (dialog.ShowDialog(this) == DialogResult.OK) {
                    preferences = dialog.Result; keepAwake.Checked = preferences.KeepAwake; ApplyKeepAwake();
                }
            }
        }

        async Task<Dictionary<string, object>> GetHealth()
        {
            try
            {
                var request = (HttpWebRequest)WebRequest.Create(HealthUrl);
                request.Proxy = null; request.Timeout = 1200; request.ReadWriteTimeout = 1200;
                using (var response = await request.GetResponseAsync())
                using (var reader = new StreamReader(response.GetResponseStream())) {
                    var health = new JavaScriptSerializer().Deserialize<Dictionary<string, object>>(await reader.ReadToEndAsync());
                    var phone = health.ContainsKey("phone") ? health["phone"] as Dictionary<string, object> : null;
                    Program.PhoneDiscoveryReady = phone != null && phone.ContainsKey("discovery_available") && (bool)phone["discovery_available"];
                    string host = phone != null && phone.ContainsKey("hostname") ? phone["hostname"] as string : null;
                    Program.PhoneHost = host != null && System.Text.RegularExpressions.Regex.IsMatch(host, "^deckedge-[a-f0-9]{12}\\.local$") ? host : null;
                    return health;
                }
            }
            catch { return null; }
        }

        async Task StartServices()
        {
            if (starting || quitting) return;
            starting = true;
            message.Visible = true; message.BringToFront();
            message.Text = "DeckEdge\n\nDémarrage du serveur…";
            try
            {
                await EnsureWebViewRuntime();
                var health = await GetHealth();
                if (quitting) return;
                if (health != null && (!health.ContainsKey("app") || (string)health["app"] != "DeckEdge"))
                    throw new InvalidOperationException("Le port 5000 est déjà utilisé. Arrêtez l'ancien serveur DeckEdge avant de réessayer.");
                if (health == null)
                {
                    if (backend != null && !backend.HasExited) throw new InvalidOperationException("Le serveur ne répond plus. Quittez DeckEdge puis relancez-le.");
                    string python = await Task.Run(() => FindPython());
                    if (quitting) return;
                    var info = new ProcessStartInfo(python, Quote(Path.Combine(Program.Project, "desktop_backend.py"))) {
                        WorkingDirectory = Program.Project, UseShellExecute = false, CreateNoWindow = true,
                        RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true
                    };
                    info.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
                    info.EnvironmentVariables["DECKEDGE_DATA_DIR"] = Program.DataDirectory;
                    info.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"] = "1";
                    var lan = PhoneConnection.Addresses(Program.PhoneKey, false).FirstOrDefault();
                    if (lan != null) info.EnvironmentVariables["DECKEDGE_LAN_IP"] = new Uri(lan.Url).Host;
                    backend = new Process { StartInfo = info };
                    backend.OutputDataReceived += CaptureBackend;
                    backend.ErrorDataReceived += CaptureBackend;
                    backend.Start();
                    backendInput = new StreamWriter(backend.StandardInput.BaseStream, new UTF8Encoding(false)) { AutoFlush = true };
                    backend.BeginOutputReadLine(); backend.BeginErrorReadLine();
                    Program.Log("Serveur lancé, PID " + backend.Id);
                    for (int i = 0; i < 80 && !quitting; i++) {
                        health = await GetHealth();
                        if (health != null) break;
                        if (backend.HasExited) throw new InvalidOperationException("Le serveur s'est arrêté au démarrage. Consultez le journal pour connaître la dépendance en cause.");
                        await Task.Delay(250);
                    }
                    if (health == null && !quitting) throw new InvalidOperationException("Le serveur n'est pas prêt après 20 secondes. Consultez le journal, puis réessayez.");
                }
                if (quitting) return;
                // Les capteurs ne bloquent pas l'ouverture du Studio s'ils demandent une élévation.
                string driverNotice = Path.Combine(Program.DataDirectory, ".driver-notice");
                using (var machine = Microsoft.Win32.RegistryKey.OpenBaseKey(Microsoft.Win32.RegistryHive.LocalMachine, Microsoft.Win32.RegistryView.Registry64))
                using (var driver = machine.OpenSubKey(@"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\PawnIO")) {
                    if (preferences.FullSensorAccess && driver == null && !File.Exists(driverNotice) && File.Exists(Path.Combine(Program.Project, "prerequisites", "PawnIO_setup.exe"))) {
                        File.WriteAllText(driverNotice, "Information pilote affichée.");
                        if (MessageBox.Show(this, "Pour afficher certaines températures et mesures matérielles, DeckEdge utilise le pilote PawnIO.\n\nL’installer maintenant ? Windows demandera votre accord. Vous pourrez aussi le faire plus tard depuis l’icône DeckEdge près de l’horloge.", "Mesures matérielles", MessageBoxButtons.YesNo, MessageBoxIcon.Information) == DialogResult.Yes)
                            await InstallHardwareDriver();
                    }
                }
                await StartSensors();
                if (quitting) return;
                message.Text = "DeckEdge\n\nOuverture du Studio…";
                if (view.CoreWebView2 == null) {
                    var environment = await CoreWebView2Environment.CreateAsync(null, Path.Combine(Program.DataDirectory, ".desktop-profile"));
                    await view.EnsureCoreWebView2Async(environment);
                    view.CoreWebView2.Settings.AreDevToolsEnabled = false;
                    view.CoreWebView2.Settings.IsStatusBarEnabled = false;
                    view.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
                    view.CoreWebView2.WebMessageReceived += delegate(object sender, CoreWebView2WebMessageReceivedEventArgs e) {
                        if (e.Source != AdminUrl) return;
                        try {
                            var data = new JavaScriptSerializer().Deserialize<Dictionary<string, object>>(e.WebMessageAsJson);
                            if (data.ContainsKey("type") && (string)data["type"] == "openSettings") OpenSettings();
                            else if (data.ContainsKey("type") && (string)data["type"] == "pickColor") PickStudioColor(data);
                            else if (data.ContainsKey("type") && (string)data["type"] == "editorDirty")
                                editorDirty = data.ContainsKey("dirty") && data["dirty"] is bool && (bool)data["dirty"];
                        } catch (Exception ex) { Program.Log("Message Studio: " + ex.Message); }
                    };
                    view.CoreWebView2.NewWindowRequested += delegate(object sender, CoreWebView2NewWindowRequestedEventArgs e) { e.Handled = true; };
                    view.CoreWebView2.NavigationStarting += delegate(object sender, CoreWebView2NavigationStartingEventArgs e) {
                        Uri uri;
                        if (!Uri.TryCreate(e.Uri, UriKind.Absolute, out uri) || uri.Scheme != "http" || uri.Host != "127.0.0.1" || uri.Port != 5000) e.Cancel = true;
                    };
                    view.CoreWebView2.NavigationCompleted += delegate(object sender, CoreWebView2NavigationCompletedEventArgs e) {
                        if (e.IsSuccess) { message.Visible = false; Program.Log("Studio WebView2 prêt."); }
                        else ShowError("Le Studio n'a pas pu s'afficher. Cliquez sur Réessayer.");
                    };
                }
                view.CoreWebView2.Navigate(AdminUrl);
                await RefreshHealth();
            }
            catch (Exception ex) { Program.Log(ex.ToString()); if (!quitting) ShowError(ex.Message); }
            finally { starting = false; }
        }

        void CaptureBackend(object sender, DataReceivedEventArgs e)
        {
            if (e.Data == null) return;
            Program.Log("Python: " + e.Data);
        }

        void PickStudioColor(Dictionary<string, object> request)
        {
            string field = request.ContainsKey("field") ? request["field"] as string : null;
            string token = request.ContainsKey("requestId") ? request["requestId"] as string : null;
            if ((field != "color" && field != "active_color") || String.IsNullOrEmpty(token) || token.Length > 100) return;
            string color = null, error = null;
            try {
                if (request.ContainsKey("mode") && (string)request["mode"] == "palette") {
                    using (var dialog = new ColorDialog { FullOpen = true, AnyColor = true }) {
                        string initial = request.ContainsKey("color") ? request["color"] as string : null;
                        if (initial != null && System.Text.RegularExpressions.Regex.IsMatch(initial, "^#[0-9a-fA-F]{6}$")) dialog.Color = ColorTranslator.FromHtml(initial);
                        if (dialog.ShowDialog(this) == DialogResult.OK) color = ToHex(dialog.Color);
                    }
                } else {
                    Color? picked = ScreenColorPicker.Pick(this);
                    if (picked.HasValue) color = ToHex(picked.Value);
                }
            } catch (Exception ex) { Program.Log("Choix de couleur: " + ex); error = "Impossible d'ouvrir le sélecteur de couleur."; }
            if (!quitting && view.CoreWebView2 != null)
                view.CoreWebView2.PostWebMessageAsJson(new JavaScriptSerializer().Serialize(new { type = "colorPicked", requestId = token, color = color, error = error }));
        }

        static string ToHex(Color color) { return String.Format("#{0:X2}{1:X2}{2:X2}", color.R, color.G, color.B); }

        async Task EnsureWebViewRuntime()
        {
            try { CoreWebView2Environment.GetAvailableBrowserVersionString(); return; }
            catch (WebView2RuntimeNotFoundException) { }
            string installer = Path.Combine(Program.Project, "prerequisites", "MicrosoftEdgeWebview2Setup.exe");
            if (!File.Exists(installer) || MessageBox.Show(this, "Le composant Microsoft WebView2 est nécessaire pour afficher le Studio.\n\nL’installer maintenant ? Une connexion Internet est nécessaire.", "DeckEdge", MessageBoxButtons.YesNo, MessageBoxIcon.Information) != DialogResult.Yes)
                throw new InvalidOperationException("Installez Microsoft WebView2 Runtime depuis le site de Microsoft, puis relancez DeckEdge.");
            await Task.Run(() => { using (var process = Process.Start(new ProcessStartInfo(installer, "/silent /install") { UseShellExecute = false, CreateNoWindow = true })) {
                process.WaitForExit(); if (process.ExitCode != 0) throw new InvalidOperationException("L’installation de WebView2 a échoué. Installez le Runtime depuis le site de Microsoft.");
            }});
            CoreWebView2Environment.GetAvailableBrowserVersionString();
        }

        async Task InstallHardwareDriver()
        {
            string installer = Path.Combine(Program.Project, "prerequisites", "PawnIO_setup.exe");
            if (!File.Exists(installer)) return;
            try {
                await Task.Run(() => { using (var process = Process.Start(new ProcessStartInfo(installer) { UseShellExecute = true, Verb = "runas" })) { process.WaitForExit(); }});
                MessageBox.Show(this, "Si l’installation du pilote a réussi, quittez puis relancez DeckEdge pour actualiser les capteurs.", "DeckEdge", MessageBoxButtons.OK, MessageBoxIcon.Information);
            } catch (System.ComponentModel.Win32Exception ex) { if (ex.NativeErrorCode != 1223) Program.Log("Installation PawnIO : " + ex.Message); }
        }

        static string FindPython()
        {
            var candidates = new List<string>();
            candidates.Add(Path.Combine(Program.Project, "runtime", "python.exe"));
            candidates.Add(Path.Combine(Program.Project, ".venv", "Scripts", "python.exe"));
            string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            foreach (string folder in new[] { Path.Combine(local, "Python"), Path.Combine(local, "Programs", "Python") })
                if (Directory.Exists(folder)) candidates.AddRange(Directory.GetDirectories(folder).OrderByDescending(d => d).Select(d => Path.Combine(d, "python.exe")));
            foreach (string folder in (Environment.GetEnvironmentVariable("PATH") ?? "").Split(';'))
                if (!String.IsNullOrWhiteSpace(folder) && folder.IndexOf("WindowsApps", StringComparison.OrdinalIgnoreCase) < 0) candidates.Add(Path.Combine(folder.Trim('"'), "python.exe"));
            foreach (string candidate in candidates.Distinct()) {
                if (!File.Exists(candidate)) continue;
                try {
                    var info = new ProcessStartInfo(candidate, Quote(Path.Combine(Program.Project, "desktop_backend.py")) + " --check") {
                        WorkingDirectory = Program.Project, UseShellExecute = false, CreateNoWindow = true,
                        RedirectStandardOutput = true, RedirectStandardError = true
                    };
                    info.EnvironmentVariables["DECKEDGE_DATA_DIR"] = Program.DataDirectory;
                    info.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"] = "1";
                    using (var process = Process.Start(info)) {
                        process.BeginOutputReadLine();
                        process.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs e) { if (e.Data != null) Program.Log("Vérification Python: " + e.Data); };
                        process.BeginErrorReadLine();
                        if (!process.WaitForExit(12000)) { process.Kill(); continue; }
                        if (process.ExitCode == 0) return candidate;
                    }
                } catch (Exception ex) { Program.Log(ex.Message); }
            }
            throw new InvalidOperationException("Python et les dépendances DeckEdge sont introuvables. Consultez le README et desktop.log.");
        }

        async Task StartSensors()
        {
            if (sensorBridge != null && sensorBridge.IsRunning) return;
            if (backend == null || backend.HasExited) throw new InvalidOperationException("Quittez l'ancien serveur et relancez DeckEdge pour activer le moteur intégré.");
            sensorBridge = new SensorBridge();
            try {
                await sensorBridge.StartAsync(line => {
                    lock (backendInputLock) {
                        if (!quitting && backend != null && !backend.HasExited) {
                            backendInput.WriteLine(line);
                        }
                    }
                }, preferences.FullSensorAccess);
            } catch (Exception ex) {
                Program.Log("Capteurs intégrés: " + ex.Message);
                tray.ShowBalloonTip(6000, "DeckEdge — capteurs", ex.Message, ToolTipIcon.Warning);
            }
        }

        async Task CheckSensors()
        {
            if (quitting) return;
            await StartSensors();
            await Task.Delay(1500);
            var health = await GetHealth();
            var sensors = health != null && health.ContainsKey("monitoring") ? health["monitoring"] as Dictionary<string, object> : null;
            if (sensors != null && sensors.ContainsKey("connected") && (bool)sensors["connected"]) {
                tray.ShowBalloonTip(4000, "DeckEdge", "Le moteur intégré reçoit les mesures du PC.", ToolTipIcon.Info);
            } else {
                MessageBox.Show("Le moteur intégré peut mettre quelques secondes à détecter les composants. Acceptez sa demande Windows pour accéder à tous les capteurs, notamment aux températures CPU.", "DeckEdge — capteurs");
            }
        }

        async Task RefreshHealth()
        {
            if (polling || quitting) return;
            polling = true;
            try {
                var health = await GetHealth();
                if (quitting) return;
                bool alive = health != null && health.ContainsKey("app") && (string)health["app"] == "DeckEdge";
                serverStatus.Text = alive ? "● Serveur prêt" : "● Serveur indisponible";
                serverStatus.ForeColor = alive ? Color.FromArgb(178, 199, 151) : Color.FromArgb(226, 140, 128);
                var sensors = alive && health.ContainsKey("monitoring") ? health["monitoring"] as Dictionary<string, object> : null;
                bool connected = sensors != null && sensors.ContainsKey("connected") && (bool)sensors["connected"];
                bool fullAccess = sensors != null && sensors.ContainsKey("elevated") && (bool)sensors["elevated"];
                sensorStatus.Text = connected ? (fullAccess ? "● Capteurs intégrés" : "○ Capteurs intégrés · accès limité") : "○ Capteurs en attente — menu : Vérifier les capteurs";
                sensorStatus.ForeColor = connected ? Color.FromArgb(178, 199, 151) : Color.FromArgb(223, 185, 121);
                tray.Text = alive ? "DeckEdge — " + (connected ? "prêt" : "capteurs en attente") : "DeckEdge — serveur indisponible";
            } finally { polling = false; }
        }

        void ShowError(string error)
        {
            message.Text = "Impossible d'ouvrir le Studio\n\n" + error;
            message.Visible = true; message.BringToFront();
            Controls["retry"].Visible = true; Controls["retry"].BringToFront();
        }

        void OnPowerChanged(object sender, Microsoft.Win32.PowerModeChangedEventArgs e)
        {
            if (e.Mode == Microsoft.Win32.PowerModes.Resume && !quitting && IsHandleCreated)
                BeginInvoke(new Action(delegate { ApplyKeepAwake(); }));
        }

        void OnSessionEnding(object sender, Microsoft.Win32.SessionEndingEventArgs e)
        {
            // La session Windows ferme le canal du serveur même en cas d'arrêt forcé.
            quitting = true;
            if (sensorBridge != null) sensorBridge.Dispose();
            try { lock (backendInputLock) { if (backendInput != null) backendInput.Close(); } } catch { }
        }

        bool ConfirmQuit()
        {
            if (!editorDirty) return true;
            RestoreStudio();
            return MessageBox.Show(this, "Le Studio contient des modifications non enregistrées.\n\nQuitter sans les enregistrer ?", "DeckEdge", MessageBoxButtons.YesNo, MessageBoxIcon.Warning, MessageBoxDefaultButton.Button2) == DialogResult.Yes;
        }

        void RequestQuit() { if (!quitting && ConfirmQuit()) { quitting = true; Close(); } }

        async void OnClosing(object sender, FormClosingEventArgs e)
        {
            if (e.CloseReason == CloseReason.WindowsShutDown || e.CloseReason == CloseReason.TaskManagerClosing) quitting = true;
            if (!quitting && preferences.CloseToTray) {
                SaveWindowPreferences();
                e.Cancel = true; Hide();
                if (!notified) {
                    notified = true;
                    tray.ShowBalloonTip(4000, "DeckEdge reste actif", "Le pupitre reste connecté. Double-cliquez sur l'icône pour rouvrir le Studio.", ToolTipIcon.Info);
                }
                return;
            }
            if (!quitting && !ConfirmQuit()) { e.Cancel = true; return; }
            quitting = true;
            if (cleaning) return;
            SaveWindowPreferences();
            e.Cancel = true; cleaning = true; timer.Stop(); Enabled = false;
            SetThreadExecutionState(0x80000000u);
            if (sensorBridge != null) sensorBridge.Dispose();
            try {
                if (backend != null && !backend.HasExited) {
                    lock (backendInputLock) backendInput.Close();
                    bool stopped = await Task.Run(() => backend.WaitForExit(5000));
                    if (!stopped) backend.Kill();
                }
            } catch (Exception ex) { Program.Log("Arrêt: " + ex.Message); }
            Microsoft.Win32.SystemEvents.SessionEnding -= OnSessionEnding;
            Microsoft.Win32.SystemEvents.PowerModeChanged -= OnPowerChanged;
            tray.Visible = false; tray.Dispose(); view.Dispose();
            Program.Log("DeckEdge arrêté.");
            Close();
        }
    }
}
