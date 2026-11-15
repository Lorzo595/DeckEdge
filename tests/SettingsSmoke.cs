using System;
using System.IO;
using System.Windows.Forms;
using System.Runtime.InteropServices;

namespace DeckEdgeDesktop
{
    // Banc de contrôle des fichiers de préférences, sans écrire au démarrage Windows.
    internal static class Program
    {
        internal static string Project;
        internal static string DataDirectory;
        internal static void Log(string message) { Console.WriteLine(message); }
        [DllImport("kernel32.dll")] static extern uint SetThreadExecutionState(uint flags);
        [STAThread]
        static void Main(string[] args)
        {
            Project = args[0]; DataDirectory = Project; Directory.CreateDirectory(Project);
            uint previous = SetThreadExecutionState(KeepAwakeController.Continuous);
            try {
                if (!KeepAwakeController.Apply(true)) throw new Exception("Windows refuse le maintien en éveil.");
                uint active = SetThreadExecutionState(KeepAwakeController.Continuous);
                if ((active & 3u) != 3u) throw new Exception("Le PC et l'écran ne sont pas tous deux protégés.");
                if (!KeepAwakeController.Apply(false)) throw new Exception("Libération du maintien en éveil impossible.");
                uint inactive = SetThreadExecutionState(KeepAwakeController.Continuous);
                if ((inactive & 3u) != 0) throw new Exception("La protection reste active après désactivation.");
            } finally { SetThreadExecutionState(previous); }
            var defaults = PreferencesStore.Load();
            if (!defaults.CloseToTray || !defaults.StartupInTray || !defaults.KeepAwake || !defaults.FullSensorAccess || defaults.ServerPort != 5000)
                throw new Exception("Valeurs par défaut incorrectes.");
            if (!PreferencesStore.StartupCommand.StartsWith("\"" + Application.ExecutablePath + "\"") || !PreferencesStore.StartupCommand.EndsWith(" --startup"))
                throw new Exception("Commande de démarrage non protégée pour les chemins avec espaces.");
            defaults.CloseToTray = false; defaults.KeepAwake = false; defaults.FullSensorAccess = false;
            defaults.WindowWidth = 1024; defaults.WindowHeight = 700; defaults.ServerPort = 5012;
            PreferencesStore.Save(defaults, false);
            var restored = PreferencesStore.Load();
            if (restored.CloseToTray || restored.KeepAwake || restored.FullSensorAccess || restored.WindowWidth != 1024 || restored.ServerPort != 5012)
                throw new Exception("Préférences non restaurées.");
            var applied = SettingsForm.BuildResult(restored, false, false, false, false, false, "fr");
            if (applied.ServerPort != 5012)
                throw new Exception("Le port serveur n'est pas conservé après « Appliquer ».");
            if (applied.Language != "fr")
                throw new Exception("La langue choisie n'est pas conservée après « Appliquer ».");
            UiText.SetLanguage("en");
            if (UiText.T("Paramètres de DeckEdge") != "DeckEdge Settings" || UiText.T("Texte inconnu") != "Texte inconnu")
                throw new Exception("Traduction de l'interface incorrecte.");
            UiText.SetLanguage("fr");
            if (UiText.T("Paramètres de DeckEdge") != "Paramètres de DeckEdge")
                throw new Exception("Le français devrait rester inchangé.");
            using (var label = new Label { Text = "Langue" }) {
                UiText.SetLanguage("en"); UiText.Translate(label);
                if (label.Text != "Language") throw new Exception("Libellé de paramètres non traduit.");
                UiText.SetLanguage("fr"); UiText.Translate(label);
                if (label.Text != "Langue") throw new Exception("Libellé français non restauré après bascule.");
            }
            using (var menu = new ContextMenuStrip()) {
                menu.Items.Add("Ouvrir le Studio");
                UiText.SetLanguage("en"); UiText.TranslateItems(menu.Items);
                if (menu.Items[0].Text != "Open Studio") throw new Exception("Menu non traduit.");
                UiText.SetLanguage("fr"); UiText.TranslateItems(menu.Items);
                if (menu.Items[0].Text != "Ouvrir le Studio") throw new Exception("Menu français non restauré après bascule.");
            }
            restored.Language = "en"; PreferencesStore.Save(restored, false);
            if (PreferencesStore.Load().Language != "en")
                throw new Exception("La langue n'est pas restaurée depuis les préférences.");
            restored.WindowMaximized = true; PreferencesStore.Save(restored, false);
            if (!PreferencesStore.Load().WindowMaximized || File.Exists(Path.Combine(Project,"app-settings.json.tmp")))
                throw new Exception("Écriture atomique incorrecte.");
            File.WriteAllText(Path.Combine(Project,"app-settings.json"), "{\"WindowWidth\":1100}");
            var legacy = PreferencesStore.Load();
            if (!legacy.KeepAwake || !legacy.CloseToTray || legacy.WindowWidth != 1100)
                throw new Exception("Migration d'un fichier partiel incorrecte.");
            Console.WriteLine("OK : valeurs par défaut, préférences persistées, écriture atomique, migration et commande de démarrage. Registre de démarrage inchangé.");
        }
    }
}
