using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace DeckEdgeDesktop
{
    internal sealed class UpdatesForm : Form
    {
        readonly Label state = new Label { AutoSize = true, MaximumSize = new Size(490, 0), Margin = new Padding(0, 12, 0, 14) };
        readonly TextBox notes = new TextBox { ReadOnly = true, Multiline = true, ScrollBars = ScrollBars.Vertical, Width = 490, Height = 190 };
        readonly Button check = new Button { AutoSize = true };
        readonly Button install = new Button { AutoSize = true, Enabled = false };
        readonly Button cancel = new Button { AutoSize = true };
        readonly CheckBox previews = new CheckBox { AutoSize = true };
        readonly ProgressBar progress = new ProgressBar { Width = 490, Height = 15 };
        readonly Func<string, bool> beginInstall;
        readonly Func<bool> canInstall;
        readonly Version current = typeof(UpdatesForm).Assembly.GetName().Version;
        CancellationTokenSource transfer;
        AppRelease release;
        string work;
        bool handedOff;

        internal UpdatesForm(Func<string, bool> installer, bool checkOnOpen = true, Func<bool> ready = null)
        {
            beginInstall = installer;
            canInstall = ready ?? (() => true);
            Text = UiText.T("Mises à jour de DeckEdge"); ClientSize = new Size(550, 480);
            StartPosition = FormStartPosition.CenterParent; FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false; MinimizeBox = false; ShowInTaskbar = false;
            BackColor = Color.FromArgb(27, 29, 26); ForeColor = Color.FromArgb(238, 238, 231); Font = new Font("Segoe UI", 10);
            var layout = new FlowLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(24), FlowDirection = FlowDirection.TopDown, WrapContents = false };
            Controls.Add(layout);
            layout.Controls.Add(new Label { Text = UiText.F("Version installée : {0}", current.ToString(3)), AutoSize = true, Font = new Font(Font, FontStyle.Bold) });
            previews.Text = UiText.T("Inclure les préversions"); previews.Checked = current.Major == 0;
            previews.CheckedChanged += delegate { release = null; install.Enabled = false; state.Text = UiText.T("Recherchez les mises à jour pour ce choix."); };
            layout.Controls.Add(previews); layout.Controls.Add(state); layout.Controls.Add(notes); layout.Controls.Add(progress);
            var buttons = new FlowLayoutPanel { AutoSize = true, Margin = new Padding(0, 14, 0, 0) };
            check.Text = UiText.T("Rechercher"); install.Text = UiText.T("Mettre à jour et redémarrer"); cancel.Text = UiText.T("Fermer");
            buttons.WrapContents = false;
            foreach (var button in new[] { check, install, cancel }) { button.FlatStyle = FlatStyle.Flat; button.Padding = new Padding(5, 4, 5, 4); }
            install.BackColor = Color.FromArgb(223, 185, 121); install.ForeColor = Color.FromArgb(32, 28, 20);
            notes.BackColor = Color.FromArgb(36, 38, 44); notes.ForeColor = ForeColor; notes.Font = new Font("Segoe UI", 9);
            buttons.Controls.Add(check); buttons.Controls.Add(install); buttons.Controls.Add(cancel); layout.Controls.Add(buttons);
            state.Text = UiText.T("Recherche manuelle sur GitHub. Aucun téléchargement en arrière-plan.");
            check.Click += async delegate { await Check(); };
            install.Click += async delegate { await Prepare(); };
            cancel.Click += delegate { if (transfer != null) transfer.Cancel(); else Close(); };
            FormClosing += delegate { if (transfer != null) transfer.Cancel(); };
            FormClosed += delegate { if (!handedOff && work != null) TryRemoveWork(); };
            if (checkOnOpen) Shown += async delegate { await Check(); };
        }
        void Busy(bool value)
        {
            check.Enabled = !value; previews.Enabled = !value; install.Enabled = !value && release != null;
            cancel.Text = UiText.T(value ? "Annuler" : "Fermer");
            progress.Style = value ? ProgressBarStyle.Marquee : ProgressBarStyle.Blocks;
        }
        async Task Check()
        {
            transfer = new CancellationTokenSource(); var token = transfer.Token; bool include = previews.Checked;
            release = null; notes.Clear(); Busy(true); state.Text = UiText.T("Recherche des mises à jour…");
            try {
                var found = await Task.Run(() => UpdateEngine.SelectRelease(UpdateEngine.DownloadText(new Uri(UpdateEngine.ReleasesUrl), token), include));
                if (IsDisposed || token.IsCancellationRequested) return;
                if (found == null) state.Text = UiText.T("Aucune version compatible disponible pour ce choix.");
                else if (found.Version <= current) state.Text = UiText.T("DeckEdge est à jour.");
                else {
                    notes.Text = (found.body ?? "").Replace("\r\n", "\n").Replace("\n", Environment.NewLine);
                    if (!File.Exists(Path.Combine(Program.Project, "DeckEdge.exe")) || !File.Exists(Path.Combine(Program.Project, "desktop_backend.py")))
                        state.Text = UiText.T("Version de développement : utilisez une édition installée ou portable pour la mise à jour intégrée.");
                    else { release = found; state.Text = UiText.F("Version {0} disponible. Vos profils et votre téléphone seront conservés.", found.Version.ToString(3)); }
                }
            } catch (Exception ex) { ShowError(ex, token); }
            finally { transfer.Dispose(); transfer = null; if (!IsDisposed) Busy(false); }
        }
        async Task Prepare()
        {
            if (release == null || transfer != null) return;
            if (!canInstall()) { state.Text = UiText.T("Enregistrez vos modifications dans le Studio, puis réessayez."); return; }
            if (MessageBox.Show(this, UiText.T("DeckEdge va télécharger la mise à jour, se fermer puis redémarrer. Vos données seront conservées.\n\nContinuer ?"), Text, MessageBoxButtons.OKCancel, MessageBoxIcon.Information) != DialogResult.OK) return;
            transfer = new CancellationTokenSource(); var token = transfer.Token;
            Busy(true); state.Text = UiText.T("Téléchargement et vérification…");
            var selected = release;
            try {
                work = Path.Combine(Path.GetTempPath(), "DeckEdge-update-" + Guid.NewGuid().ToString("N")); Directory.CreateDirectory(work);
                var report = new Progress<int>(value => { if (!IsDisposed) { progress.Style = ProgressBarStyle.Blocks; progress.Value = Math.Min(100, value); } });
                string directory = work;
                await Task.Run(() => {
                    string sums = UpdateEngine.DownloadText(UpdateEngine.AssetUri(selected, selected.Checksums), token);
                    string hash = UpdateEngine.ExpectedHash(sums, selected.Package.name);
                    string zip = Path.Combine(directory, "package.zip");
                    using (var stream = new FileStream(zip, FileMode.CreateNew))
                        UpdateEngine.Download(UpdateEngine.AssetUri(selected, selected.Package), stream, selected.Package.size, token,
                            bytes => ((IProgress<int>)report).Report((int)(bytes * 100 / selected.Package.size)));
                    if (new FileInfo(zip).Length != selected.Package.size) throw new InvalidDataException("Incomplete update download.");
                    UpdateEngine.VerifyHash(zip, hash);
                    // Validate all entries now, before asking the running app to exit.
                    UpdateEngine.Extract(zip, Path.Combine(directory, "payload"), selected.Version.ToString(3), token);
                    Directory.Delete(Path.Combine(directory, "payload"), true);
                    var process = Process.GetCurrentProcess();
                    var plan = new UpdatePlan { Target = Path.GetFullPath(Program.Project), Version = selected.Version.ToString(3), Sha256 = hash,
                        Portable = File.Exists(Path.Combine(Program.Project, "portable.flag")), ProcessId = process.Id, ProcessStart = process.StartTime.ToUniversalTime().Ticks, Language = UiText.Language,
                        DataDirectory = Path.GetFullPath(Program.DataDirectory) };
                    UpdateEngine.ValidateTarget(plan);
                    File.WriteAllText(Path.Combine(directory, "plan.json"), new JavaScriptSerializer().Serialize(plan));
                    File.Copy(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "DeckEdge.Updater.exe"), Path.Combine(directory, "DeckEdge.Updater.exe"));
                });
                token.ThrowIfCancellationRequested();
                if (!IsDisposed) {
                    // Closing an owner can dispose this dialog synchronously. Keep
                    // the helper's directory alive before calling back into it.
                    handedOff = true;
                    try { handedOff = beginInstall(Path.Combine(directory, "plan.json")); }
                    catch { handedOff = false; throw; }
                    if (handedOff) Close();
                    else state.Text = UiText.T("Enregistrez vos modifications dans le Studio, puis réessayez.");
                }
            } catch (Exception ex) { ShowError(ex, token); }
            finally {
                transfer.Dispose(); transfer = null;
                if (!handedOff) TryRemoveWork();
                if (!IsDisposed) Busy(false);
            }
        }
        void ShowError(Exception ex, CancellationToken token)
        {
            Program.Log("Update: " + ex.Message);
            if (!IsDisposed) state.Text = token.IsCancellationRequested ? UiText.T("Mise à jour annulée. Aucun fichier de l’application n’a été modifié.")
                : ex is InvalidDataException ? UiText.T("Le fichier de mise à jour est incomplet ou non valide. Aucun fichier de l’application n’a été modifié.")
                : UiText.T("La mise à jour n’a pas pu être préparée. Vous pouvez réessayer ; l’application reste utilisable.");
        }
        void TryRemoveWork()
        {
            // Only the GUID-owned download directory created by this dialog.
            if (work == null) return;
            try { UpdateEngine.AssertNoLinks(work); if (Directory.Exists(work)) Directory.Delete(work, true); work = null; } catch { }
        }
    }
}
