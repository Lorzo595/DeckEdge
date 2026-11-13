using System;
using System.Drawing;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Windows.Forms;
using System.Web.Script.Serialization;
using Microsoft.Win32;

namespace DeckEdgeDesktop
{
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

        internal static bool StartupEnabled()
        {
            using (var key = Registry.CurrentUser.OpenSubKey(RunKey))
                return key != null && String.Equals(key.GetValue(RunName) as string, StartupCommand, StringComparison.OrdinalIgnoreCase);
        }

        internal static AppPreferences Load()
        {
            var prefs = new AppPreferences();
            try {
                if (File.Exists(FilePath)) prefs = new JavaScriptSerializer().Deserialize<AppPreferences>(File.ReadAllText(FilePath)) ?? prefs;
            } catch (Exception ex) { Program.Log("Lecture paramètres: " + ex.Message); }
            try { prefs.StartWithWindows = StartupEnabled(); } catch (Exception ex) { Program.Log("Lecture démarrage Windows: " + ex.Message); }
            return prefs;
        }

        static void SetStartup(bool enabled)
        {
            if (enabled) {
                if (StartupCommand.Length > 260) throw new InvalidOperationException("Le chemin de l'application est trop long pour le démarrage Windows. Déplacez le projet dans un dossier plus court.");
                using (var key = Registry.CurrentUser.CreateSubKey(RunKey)) key.SetValue(RunName, StartupCommand, RegistryValueKind.String);
            } else if (StartupEnabled()) {
                using (var key = Registry.CurrentUser.OpenSubKey(RunKey, true)) if (key != null) key.DeleteValue(RunName, false);
            }
        }

        internal static void Save(AppPreferences prefs, bool updateStartup)
        {
            string temporary = FilePath + ".tmp";
            bool previousStartup = false, changedStartup = false;
            try {
                File.WriteAllText(temporary, new JavaScriptSerializer().Serialize(prefs));
                if (updateStartup) {
                    previousStartup = StartupEnabled();
                    if (previousStartup != prefs.StartWithWindows) { SetStartup(prefs.StartWithWindows); changedStartup = true; }
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
            closeTray = Check(layout, "Continuer en arrière-plan quand je ferme la fenêtre", preferences.CloseToTray);
            awake = Check(layout, "Empêcher la mise en veille pendant l'utilisation", preferences.KeepAwake);
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
