using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Win32;

namespace DeckEdgeDesktop
{
    internal static class UpdaterMain
    {
        [STAThread]
        static void Main(string[] args)
        {
            Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
            if (args.Length != 1) return;
            string directory = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
            var work = new DirectoryInfo(directory);
            if (!Regex.IsMatch(work.Name, "^DeckEdge-update-[a-f0-9]{32}$") || work.Parent == null
                || !String.Equals(work.Parent.FullName.TrimEnd(Path.DirectorySeparatorChar), Path.GetFullPath(Path.GetTempPath()).TrimEnd(Path.DirectorySeparatorChar), StringComparison.OrdinalIgnoreCase)) return;
            string expected = Path.Combine(directory, "plan.json");
            if (!String.Equals(Path.GetFullPath(args[0]), expected, StringComparison.OrdinalIgnoreCase)) return;
            UpdatePlan plan;
            try {
                UpdateEngine.AssertNoLinks(directory);
                plan = new JavaScriptSerializer().Deserialize<UpdatePlan>(File.ReadAllText(expected));
                UpdateEngine.ValidateTarget(plan);
            } catch (Exception ex) { MessageBox.Show("Invalid DeckEdge update: " + ex.Message, "DeckEdge"); return; }
            UiText.SetLanguage(plan.Language);
            var window = new Form { Text = UiText.T("Mise à jour de DeckEdge"), ClientSize = new Size(470, 130), StartPosition = FormStartPosition.CenterScreen,
                FormBorderStyle = FormBorderStyle.FixedDialog, MaximizeBox = false, MinimizeBox = false, ControlBox = false };
            var label = new Label { Text = UiText.T("Fermeture de DeckEdge et installation de la mise à jour…"), AutoSize = false, Dock = DockStyle.Fill, Padding = new Padding(22), Font = new Font("Segoe UI", 11) };
            window.Controls.Add(label);
            window.Shown += async delegate {
                bool stopped = false, restart = false, launched = false;
                try {
                    await Task.Run(() => {
                        try {
                            using (var process = Process.GetProcessById(plan.ProcessId)) {
                                if (process.StartTime.ToUniversalTime().Ticks != plan.ProcessStart || !process.WaitForExit(120000)) throw new IOException("DeckEdge is still running.");
                            }
                        } catch (ArgumentException) { /* The requested process already exited. */ }
                        stopped = true;
                        using (var mutex = new Mutex(false, UpdateEngine.InstanceKey(plan.Target))) {
                            bool acquired;
                            try { acquired = mutex.WaitOne(0); } catch (AbandonedMutexException) { acquired = true; }
                            if (!acquired) { stopped = false; throw new IOException("Another DeckEdge instance was opened."); }
                            try {
                                UpdateEngine.VerifyHash(Path.Combine(directory, "package.zip"), plan.Sha256);
                                // Re-extract the verified archive so the prepared payload cannot drift.
                                string payload = Path.Combine(directory, "verified");
                                UpdateEngine.Extract(Path.Combine(directory, "package.zip"), payload, plan.Version, CancellationToken.None);
                                UpdateEngine.Apply(plan, payload, Path.Combine(directory, "backup"), null);
                                restart = true;
                                if (!plan.Portable) UpdateUninstallVersion(plan);
                            } finally { mutex.ReleaseMutex(); }
                        }
                    });
                } catch (Exception ex) {
                    string message = ex is AggregateException
                        ? UiText.T("La mise à jour a échoué et la restauration est incomplète. Conservez la sauvegarde : ") + Path.Combine(directory, "backup")
                        : UiText.T("La mise à jour a échoué. Les fichiers précédents ont été conservés ou restaurés.");
                    MessageBox.Show(window, message, "DeckEdge", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    restart = stopped && !(ex is AggregateException);
                    try { File.WriteAllText(Path.Combine(directory, "error.txt"), ex.ToString()); } catch { }
                }
                if (restart) try {
                    var info = new ProcessStartInfo(Path.Combine(plan.Target, "DeckEdge.exe")) { WorkingDirectory = plan.Target, UseShellExecute = false };
                    if (!String.IsNullOrEmpty(plan.DataDirectory)) info.EnvironmentVariables["DECKEDGE_DATA_DIR"] = plan.DataDirectory;
                    Process.Start(info); launched = true;
                } catch { MessageBox.Show(window, UiText.T("Vous pouvez rouvrir DeckEdge depuis son raccourci."), "DeckEdge"); }
                // A successful replacement no longer needs the archive/extraction
                // copies. On failure keep the backup and error report for recovery.
                if (launched && !File.Exists(Path.Combine(directory, "error.txt"))) try {
                    foreach (string folder in new[] { "payload", "verified", "backup" }) {
                        string path = Path.Combine(directory, folder); UpdateEngine.AssertNoLinks(path);
                        if (Directory.Exists(path)) Directory.Delete(path, true);
                    }
                    File.Delete(Path.Combine(directory, "package.zip"));
                } catch { }
                window.Close();
            };
            Application.Run(window);
        }
        static void UpdateUninstallVersion(UpdatePlan plan)
        {
            // Registration is optional; never modify another installation's entry.
            try {
                using (var key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\{4A8E0309-846A-4E17-827B-8154D77C4060}_is1", true)) {
                    string location = key == null ? null : key.GetValue("InstallLocation") as string;
                    if (location != null && String.Equals(Path.GetFullPath(location).TrimEnd('\\'), Path.GetFullPath(plan.Target).TrimEnd('\\'), StringComparison.OrdinalIgnoreCase))
                        key.SetValue("DisplayVersion", plan.Version);
                }
            } catch { }
        }
    }
}
