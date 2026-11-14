using System;
using System.Drawing;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using System.Web.Script.Serialization;
using Microsoft.Win32;

namespace DeckEdgeDesktop
{
    internal static class KeepAwakeController
    {
        internal const uint Continuous = 0x80000000u;
        internal const uint SystemAndDisplay = Continuous | 0x1u | 0x2u;
        [DllImport("kernel32.dll")] static extern uint SetThreadExecutionState(uint flags);
        internal static bool Apply(bool enabled)
        {
            return SetThreadExecutionState(enabled ? SystemAndDisplay : Continuous) != 0;
        }
    }

    public sealed class AppPreferences
    {
        public bool StartWithWindows { get; set; }
        public bool StartupInTray { get; set; }
        public bool CloseToTray { get; set; }
        public bool KeepAwake { get; set; }
        public bool FullSensorAccess { get; set; }
        public int WindowWidth { get; set; }
        public int WindowHeight { get; set; }
        public bool WindowMaximized { get; set; }
        public AppPreferences() {
            StartupInTray = true; CloseToTray = true; KeepAwake = true; FullSensorAccess = true;
            WindowWidth = 1360; WindowHeight = 920;
        }
    }

    internal static class PreferencesStore
    {
        const string RunKey = @"Software\Microsoft\Windows\CurrentVersion\Run";
        const string RunName = "DeckEdge";
        static string FilePath { get { return Path.Combine(Program.DataDirectory, "app-settings.json"); } }
        internal static string StartupCommand { get { return "\"" + Application.ExecutablePath + "\" --startup"; } }
        internal static string StartupShortcut { get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Startup), "DeckEdge.lnk"); } }

        static bool DisabledByWindows(string group, string name)
        {
            using (var key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\" + group)) {
                var state = key == null ? null : key.GetValue(name) as byte[];
                return state != null && state.Length > 0 && (state[0] == 3 || state[0] == 7);
            }
        }

        static object ShortcutProperty(object shortcut, string name)
        {
            return shortcut.GetType().InvokeMember(name, BindingFlags.GetProperty, null, shortcut, null);
        }

        static bool ShortcutMatches()
        {
            if (!File.Exists(StartupShortcut)) return false;
            object shell = null, shortcut = null;
            try {
                shell = Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell"));
                shortcut = shell.GetType().InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, shell, new object[] { StartupShortcut });
                return String.Equals(Convert.ToString(ShortcutProperty(shortcut, "TargetPath")), Application.ExecutablePath, StringComparison.OrdinalIgnoreCase)
                    && Convert.ToString(ShortcutProperty(shortcut, "Arguments")) == "--startup";
            } finally {
                if (shortcut != null) Marshal.FinalReleaseComObject(shortcut);
                if (shell != null) Marshal.FinalReleaseComObject(shell);
            }
        }

        internal static bool StartupEnabled()
        {
            if (ShortcutMatches()) return !DisabledByWindows("StartupFolder", "DeckEdge.lnk");
            using (var key = Registry.CurrentUser.OpenSubKey(RunKey))
                return key != null && !DisabledByWindows("Run", RunName) && String.Equals(key.GetValue(RunName) as string, StartupCommand, StringComparison.OrdinalIgnoreCase);
        }

        internal static AppPreferences Load()
        {
            var prefs = new AppPreferences();
            try {
                if (File.Exists(FilePath)) prefs = new JavaScriptSerializer().Deserialize<AppPreferences>(File.ReadAllText(FilePath)) ?? prefs;
            } catch (Exception ex) { Program.Log("Lecture paramètres: " + ex.Message); }
            try {
                prefs.StartWithWindows = StartupEnabled();
                if (prefs.StartWithWindows && !ShortcutMatches()) SetStartup(true);
            } catch (Exception ex) { Program.Log("Lecture démarrage Windows: " + ex.Message); }
            return prefs;
        }

        static void SetStartup(bool enabled)
        {
            if (enabled) {
                if (DisabledByWindows("StartupFolder", "DeckEdge.lnk"))
                    throw new InvalidOperationException("Windows a désactivé DeckEdge au démarrage. Réactivez-le dans Paramètres Windows > Applications > Démarrage, puis réessayez.");
                Directory.CreateDirectory(Path.GetDirectoryName(StartupShortcut));
                object shell = null, shortcut = null;
                try {
                    shell = Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell"));
                    shortcut = shell.GetType().InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, shell, new object[] { StartupShortcut });
                    string[] names = { "TargetPath", "Arguments", "WorkingDirectory", "Description" };
                    string[] values = { Application.ExecutablePath, "--startup", Path.GetDirectoryName(Application.ExecutablePath), "DeckEdge au démarrage de Windows" };
                    for (int i = 0; i < names.Length; i++) shortcut.GetType().InvokeMember(names[i], BindingFlags.SetProperty, null, shortcut, new object[] { values[i] });
                    shortcut.GetType().InvokeMember("Save", BindingFlags.InvokeMethod, null, shortcut, null);
                } finally {
                    if (shortcut != null) Marshal.FinalReleaseComObject(shortcut);
                    if (shell != null) Marshal.FinalReleaseComObject(shell);
                }
                if (!ShortcutMatches()) throw new IOException("Le raccourci de démarrage n'a pas pu être vérifié.");
            } else if (ShortcutMatches()) {
                File.Delete(StartupShortcut);
            }
            // Migrate our own legacy entry without touching another installation.
            using (var key = Registry.CurrentUser.OpenSubKey(RunKey, true))
                if (key != null && String.Equals(key.GetValue(RunName) as string, StartupCommand, StringComparison.OrdinalIgnoreCase)) key.DeleteValue(RunName, false);
        }

        internal static void Save(AppPreferences prefs, bool updateStartup)
        {
            string temporary = FilePath + ".tmp";
            bool previousStartup = false, changedStartup = false;
            try {
                File.WriteAllText(temporary, new JavaScriptSerializer().Serialize(prefs));
                if (updateStartup) {
                    previousStartup = StartupEnabled();
                    SetStartup(prefs.StartWithWindows); changedStartup = true;
                }
                if (File.Exists(FilePath)) File.Replace(temporary, FilePath, null);
                else File.Move(temporary, FilePath);
            } catch {
                if (changedStartup) { try { SetStartup(previousStartup); } catch { } }
                throw;
            } finally { if (File.Exists(temporary)) File.Delete(temporary); }
        }
    }

    internal sealed class SettingsForm : Form
    {
        internal AppPreferences Result;
        readonly AppPreferences original;
        readonly CheckBox startup, startupTray, closeTray, awake, fullSensors;

        internal SettingsForm(AppPreferences preferences)
        {
            original = preferences;
            Text = "Paramètres de DeckEdge"; ClientSize = new Size(540, 650);
            FormBorderStyle = FormBorderStyle.FixedDialog; MaximizeBox = false; MinimizeBox = false;
            StartPosition = FormStartPosition.CenterParent; ShowInTaskbar = false;
            BackColor = Color.FromArgb(27, 29, 26); ForeColor = Color.FromArgb(238, 238, 231);
            Font = new Font("Segoe UI", 10); AutoScaleMode = AutoScaleMode.Dpi;
            var layout = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.TopDown, WrapContents = false, Padding = new Padding(26), AutoScroll = true };
            Controls.Add(layout);
            layout.Controls.Add(new Label { Text = "À votre façon.", Font = new Font("Segoe UI", 19), AutoSize = true, Margin = new Padding(0, 0, 0, 17) });
            startup = Check(layout, "Lancer DeckEdge à l'ouverture de ma session Windows", preferences.StartWithWindows);
            startupTray = Check(layout, "Démarrer discrètement près de l'horloge", preferences.StartupInTray);
            startupTray.Margin = new Padding(24, 3, 0, 12); startupTray.Enabled = startup.Checked;
            startup.CheckedChanged += delegate { startupTray.Enabled = startup.Checked; };
            var windowsStartup = new LinkLabel { Text = "Vérifier les applications de démarrage dans Windows", AutoSize = true, LinkColor = Color.FromArgb(223, 185, 121), Margin = new Padding(0, 0, 0, 12) };
            windowsStartup.LinkClicked += delegate { Process.Start(new ProcessStartInfo("ms-settings:startupapps") { UseShellExecute = true }); };
            layout.Controls.Add(windowsStartup);
            closeTray = Check(layout, "Continuer en arrière-plan quand je ferme la fenêtre", preferences.CloseToTray);
            awake = Check(layout, "Garder le PC et l'écran éveillés tant que DeckEdge est ouvert", preferences.KeepAwake);
            fullSensors = Check(layout, "Demander l'accès complet aux capteurs matériels", preferences.FullSensorAccess);
            layout.Controls.Add(new Label {
                Text = "L'accès complet affiche une demande Windows au lancement. Sans cet accès, certaines mesures peuvent manquer. Un changement s'applique au prochain lancement du moteur.",
                MaximumSize = new Size(470, 0), AutoSize = true, ForeColor = Color.FromArgb(163, 167, 156), Font = new Font("Segoe UI", 9), Margin = new Padding(0, 6, 0, 15)
            });
            layout.Controls.Add(new Label {
                Text = "La taille de la fenêtre est mémorisée automatiquement. Ces paramètres concernent ce PC ; les profils du pupitre sont enregistrés séparément.",
                MaximumSize = new Size(470, 0), AutoSize = true, ForeColor = Color.FromArgb(163, 167, 156), Font = new Font("Segoe UI", 9), Margin = new Padding(0, 0, 0, 15)
            });
            var assembly = typeof(SettingsForm).Assembly;
            var company = (AssemblyCompanyAttribute)Attribute.GetCustomAttribute(assembly, typeof(AssemblyCompanyAttribute));
            var about = new FlowLayoutPanel {
                FlowDirection = FlowDirection.TopDown, WrapContents = false, AutoSize = true,
                Width = 470, MinimumSize = new Size(470, 0), Padding = new Padding(16),
                BackColor = Color.FromArgb(36, 38, 44), Margin = new Padding(0, 5, 0, 16)
            };
            about.Controls.Add(new Label { Text = "À propos de DeckEdge", AutoSize = true, Font = new Font("Segoe UI", 12, FontStyle.Bold), Margin = new Padding(0, 0, 0, 10) });
            about.Controls.Add(new Label { Text = "Version " + assembly.GetName().Version.ToString(3) + " · Windows 64 bits", AutoSize = true, Margin = new Padding(0, 0, 0, 7) });
            about.Controls.Add(new Label { Text = "Développement : " + (company == null ? "DeckEdge contributors" : company.Company), MaximumSize = new Size(430, 0), AutoSize = true, Margin = new Padding(0, 0, 0, 7) });
            about.Controls.Add(new Label { Text = "Contributeurs\nLorzo595 · création et développement\nxavco63 · fiabilité des profils et de l’audio (PR #2)", MaximumSize = new Size(430, 0), AutoSize = true, Font = new Font("Segoe UI", 9), Margin = new Padding(0, 0, 0, 10) });
            about.Controls.Add(new Label { Text = "Avec l’aide de ChatGPT", AutoSize = true, Font = new Font("Segoe UI", 9), ForeColor = Color.FromArgb(173, 179, 195), Margin = new Padding(0, 0, 0, 7) });
            about.Controls.Add(new Label { Text = "Code source ouvert · Licence MIT\nCapteurs : LibreHardwareMonitor · Interface : Microsoft WebView2", MaximumSize = new Size(430, 0), AutoSize = true, Font = new Font("Segoe UI", 9), ForeColor = Color.FromArgb(173, 179, 195), Margin = new Padding(0, 0, 0, 10) });
            var license = new Button { Text = "Consulter la licence", AutoSize = true, FlatStyle = FlatStyle.Flat, Padding = new Padding(6, 3, 6, 3), Margin = new Padding(0) };
            license.Click += delegate {
                string path = Path.Combine(Program.Project, "LICENSE");
                if (File.Exists(path)) Process.Start(new ProcessStartInfo("notepad.exe", "\"" + path + "\"") { UseShellExecute = true });
                else MessageBox.Show(this, "La licence MIT est disponible dans les sources de DeckEdge.", "Licence de DeckEdge", MessageBoxButtons.OK, MessageBoxIcon.Information);
            };
            about.Controls.Add(license); layout.Controls.Add(about);
            var actions = new FlowLayoutPanel { Dock = DockStyle.Bottom, Height = 76, Padding = new Padding(26, 12, 0, 12), WrapContents = false, BackColor = BackColor };
            var save = new Button { Text = "Appliquer", AutoSize = true, FlatStyle = FlatStyle.Flat, BackColor = Color.FromArgb(223, 185, 121), ForeColor = Color.FromArgb(32, 28, 20), Padding = new Padding(12, 5, 12, 5) };
            var cancel = new Button { Text = "Annuler", AutoSize = true, FlatStyle = FlatStyle.Flat, Padding = new Padding(12, 5, 12, 5), DialogResult = DialogResult.Cancel };
            actions.Controls.Add(save); actions.Controls.Add(cancel); Controls.Add(actions);
            AcceptButton = save; CancelButton = cancel;
            save.Click += delegate {
                Result = new AppPreferences {
                    StartWithWindows = startup.Checked, StartupInTray = startupTray.Checked, CloseToTray = closeTray.Checked,
                    KeepAwake = awake.Checked, FullSensorAccess = fullSensors.Checked,
                    WindowWidth = original.WindowWidth, WindowHeight = original.WindowHeight, WindowMaximized = original.WindowMaximized
                };
                try { PreferencesStore.Save(Result, true); DialogResult = DialogResult.OK; Close(); }
                catch (Exception ex) { MessageBox.Show(this, "Impossible d'appliquer ces paramètres.\n\n" + ex.Message, "DeckEdge", MessageBoxButtons.OK, MessageBoxIcon.Error); }
            };
        }

        static CheckBox Check(FlowLayoutPanel panel, string text, bool value)
        {
            var control = new CheckBox { Text = text, Checked = value, AutoSize = true, MaximumSize = new Size(475, 0), Margin = new Padding(0, 6, 0, 12) };
            panel.Controls.Add(control); return control;
        }
    }
}
