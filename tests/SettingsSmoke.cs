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
            if (!defaults.CloseToTray || !defaults.StartupInTray || !defaults.KeepAwake || !defaults.FullSensorAccess)
                throw new Exception("Valeurs par défaut incorrectes.");
            if (!PreferencesStore.StartupCommand.StartsWith("\"" + Application.ExecutablePath + "\"") || !PreferencesStore.StartupCommand.EndsWith(" --startup"))
                throw new Exception("Commande de démarrage non protégée pour les chemins avec espaces.");
            defaults.CloseToTray = false; defaults.KeepAwake = false; defaults.FullSensorAccess = false;
            defaults.WindowWidth = 1024; defaults.WindowHeight = 700;
            PreferencesStore.Save(defaults, false);
            var restored = PreferencesStore.Load();
            if (restored.CloseToTray || restored.KeepAwake || restored.FullSensorAccess || restored.WindowWidth != 1024)
                throw new Exception("Préférences non restaurées.");
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
