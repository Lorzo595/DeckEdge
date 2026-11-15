using System;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Windows.Forms;
namespace DeckEdgeDesktop
{
    internal static class Program
    {
        internal static string Project, DataDirectory;
        internal static void Log(string value) { Console.WriteLine(value); }
        [STAThread]
        static void Main(string[] args)
        {
            Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
            Project = DataDirectory = args[0]; Directory.CreateDirectory(Project);
            foreach (string language in new[] { "fr", "en" }) {
                UiText.SetLanguage(language);
                using (var form = new UpdatesForm(_ => false, false)) {
                    form.Show(); Application.DoEvents();
                    var buttons = form.Controls[0].Controls.OfType<FlowLayoutPanel>().Single().Controls.OfType<Button>().ToArray();
                    if (buttons.Length != 3 || buttons[1].Enabled) throw new Exception("Invalid initial update controls.");
                    var previews = form.Controls[0].Controls.OfType<CheckBox>().Single();
                    if (!previews.Checked) throw new Exception("Pre-release default for 0.x builds.");
                    var state = (Label)typeof(UpdatesForm).GetField("state", BindingFlags.NonPublic | BindingFlags.Instance).GetValue(form);
                    state.Text = UiText.F("Version {0} disponible. Vos profils et votre téléphone seront conservés.", "0.1.6");
                    form.Controls[0].Controls.OfType<TextBox>().Single().Text = language == "fr" ? "Mise à jour prête.\r\n\r\nProfils et association du téléphone conservés.\r\nTéléchargement vérifié avant fermeture.\r\nRedémarrage automatique." : "Update ready.\r\n\r\nProfiles and phone pairing preserved.\r\nDownload verified before closing.\r\nAutomatic restart.";
                    Application.DoEvents();
                    foreach (var button in buttons) {
                        var bounds = form.RectangleToClient(button.RectangleToScreen(button.ClientRectangle));
                        if (!form.ClientRectangle.Contains(bounds)) throw new Exception("Update button clipped: " + language + " " + button.Text + " " + bounds);
                    }
                    using (var bitmap = new Bitmap(form.Width, form.Height)) { form.DrawToBitmap(bitmap, form.ClientRectangle); bitmap.Save(Path.Combine(Project, "updates-" + language + ".png")); }
                    form.Close();
                }
            }
            Console.WriteLine("OK: French/English update dialogs rendered; actions visible; install disabled before a release check.");
        }
    }
}
