using System;
using System.Collections.Generic;
using System.Globalization;
using System.Runtime.CompilerServices;
using System.Windows.Forms;

namespace DeckEdgeDesktop
{
    internal static class UiText
    {
        internal static string DefaultLanguage
        {
            get { return CultureInfo.CurrentUICulture.TwoLetterISOLanguageName == "fr" ? "fr" : "en"; }
        }

        private static string language = DefaultLanguage;
        internal static string Language { get { return language; } }
        internal static bool IsEnglish { get { return language == "en"; } }

        private static readonly Dictionary<string, string> English = new Dictionary<string, string>
        {
            { "Paramètres de DeckEdge", "DeckEdge Settings" },
            { "Appliquer", "Apply" },
            { "Annuler", "Cancel" },
            { "Licence de DeckEdge", "DeckEdge license" },
            { "Windows a désactivé DeckEdge au démarrage. Réactivez-le dans Paramètres Windows > Applications > Démarrage, puis réessayez.", "Windows disabled DeckEdge at startup. Re-enable it in Windows Settings > Apps > Startup, then try again." },
            { "Le raccourci de démarrage n'a pas pu être vérifié.", "The startup shortcut could not be verified." },
            { "DeckEdge au démarrage de Windows", "DeckEdge at Windows startup" },
            { "À votre façon.", "Your way." },
            { "Rechercher une mise à jour…", "Check for updates…" },
            { "Mises à jour de DeckEdge", "DeckEdge Updates" },
            { "Version installée : {0}", "Installed version: {0}" },
            { "Inclure les préversions", "Include pre-releases" },
            { "Recherchez les mises à jour pour ce choix.", "Check for updates with this choice." },
            { "Rechercher", "Check" },
            { "Mettre à jour et redémarrer", "Update and restart" },
            { "Recherche manuelle sur GitHub. Aucun téléchargement en arrière-plan.", "Manual check on GitHub. No background downloads." },
            { "Recherche des mises à jour…", "Checking for updates…" },
            { "Aucune version compatible disponible pour ce choix.", "No compatible release is available for this choice." },
            { "DeckEdge est à jour.", "DeckEdge is up to date." },
            { "Version de développement : utilisez une édition installée ou portable pour la mise à jour intégrée.", "Development build: use an installed or portable edition for in-app updates." },
            { "Version {0} disponible. Vos profils et votre téléphone seront conservés.", "Version {0} is available. Your profiles and phone pairing will be kept." },
            { "DeckEdge va télécharger la mise à jour, se fermer puis redémarrer. Vos données seront conservées.\n\nContinuer ?", "DeckEdge will download the update, close and restart. Your data will be kept.\n\nContinue?" },
            { "Téléchargement et vérification…", "Downloading and verifying…" },
            { "Enregistrez vos modifications dans le Studio, puis réessayez.", "Save your Studio changes, wait for startup to finish, then try again." },
            { "Mise à jour annulée. Aucun fichier de l’application n’a été modifié.", "Update cancelled. No application files were changed." },
            { "Le fichier de mise à jour est incomplet ou non valide. Aucun fichier de l’application n’a été modifié.", "The update file is incomplete or invalid. No application files were changed." },
            { "La mise à jour n’a pas pu être préparée. Vous pouvez réessayer ; l’application reste utilisable.", "The update could not be prepared. You can try again; the application remains usable." },
            { "Mise à jour de DeckEdge", "Updating DeckEdge" },
            { "Fermeture de DeckEdge et installation de la mise à jour…", "Closing DeckEdge and installing the update…" },
            { "La mise à jour a échoué et la restauration est incomplète. Conservez la sauvegarde : ", "The update failed and recovery is incomplete. Keep the backup: " },
            { "La mise à jour a échoué. Les fichiers précédents ont été conservés ou restaurés.", "The update failed. Previous files were kept or restored." },
            { "Vous pouvez rouvrir DeckEdge depuis son raccourci.", "You can reopen DeckEdge using its shortcut." },
            { "Langue", "Language" },
            { "Lancer DeckEdge à l'ouverture de ma session Windows", "Start DeckEdge when I sign in to Windows" },
            { "Démarrer discrètement près de l'horloge", "Start minimized in the system tray" },
            { "Vérifier les applications de démarrage dans Windows", "Check startup apps in Windows" },
            { "Continuer en arrière-plan quand je ferme la fenêtre", "Keep running in the background when I close the window" },
            { "Garder le PC et l'écran éveillés tant que DeckEdge est ouvert", "Keep the PC and display awake while DeckEdge is running" },
            { "Demander l'accès complet aux capteurs matériels", "Request full access to hardware sensors" },
            { "L'accès complet affiche une demande Windows au lancement. Sans cet accès, certaines mesures peuvent manquer. Un changement s'applique au prochain lancement du moteur.", "Full access shows a Windows prompt at launch. Without it, some readings may be missing. A change applies the next time the engine starts." },
            { "La taille de la fenêtre est mémorisée automatiquement. Ces paramètres concernent ce PC ; les profils du pupitre sont enregistrés séparément.", "The window size is saved automatically. These settings apply to this PC; deck profiles are stored separately." },
            { "À propos de DeckEdge", "About DeckEdge" },
            { "Développement : ", "Development: " },
            { "Contributeurs\nLorzo595 · création et développement\nxavco63 · interface bilingue, profils, actions et audio", "Contributors\nLorzo595 · creation and development\nxavco63 · bilingual interface, profiles, actions and audio" },
            { "Code source ouvert · Licence MIT\nCapteurs : LibreHardwareMonitor · Interface : Microsoft WebView2", "Open source · MIT License\nSensors: LibreHardwareMonitor · UI: Microsoft WebView2" },
            { "Consulter la licence", "View license" },
            { "La licence MIT est disponible dans les sources de DeckEdge.", "The MIT license is available in the DeckEdge sources." },
            { "Impossible d'appliquer ces paramètres.", "Unable to apply these settings." },
            { "DeckEdge — Studio", "DeckEdge — Studio" },
            { "DeckEdge\n\nPréparation du Studio et des capteurs…", "DeckEdge\n\nPreparing the Studio and sensors…" },
            { "DeckEdge\n\nDémarrage du serveur…", "DeckEdge\n\nStarting server…" },
            { "DeckEdge\n\nOuverture du Studio…", "DeckEdge\n\nOpening the Studio…" },
            { "Réessayer", "Retry" },
            { "Connecter le téléphone", "Connect phone" },
            { "Paramètres…", "Settings…" },
            { "Connecter le téléphone (QR code)…", "Connect phone (QR code)…" },
            { "Copier le lien du téléphone", "Copy phone link" },
            { "Vérifier les capteurs", "Check sensors" },
            { "Installer l'accès matériel (PawnIO)…", "Install hardware access (PawnIO)…" },
            { "Voir le journal", "View log" },
            { "Ouvrir les données", "Open data folder" },
            { "Quitter DeckEdge", "Quit DeckEdge" },
            { "Ouvrir le Studio", "Open Studio" },
            { "Empêcher la mise en veille", "Prevent sleep" },
            { "DeckEdge — démarrage", "DeckEdge — starting" },
            { "Démarrage du serveur…", "Starting server…" },
            { "Capteurs en attente…", "Sensors waiting…" },
            { "DeckEdge reste actif", "DeckEdge stays active" },
            { "Le pupitre reste connecté. Double-cliquez sur l'icône pour rouvrir le Studio.", "The deck stays connected. Double-click the icon to reopen the Studio." },
            { "Le Studio contient des modifications non enregistrées.\n\nQuitter sans les enregistrer ?", "The Studio has unsaved changes.\n\nQuit without saving?" },
            { "DeckEdge ne peut pas démarrer.\n\n", "DeckEdge cannot start.\n\n" },
            { "Journal : ", "Log: " },
            { "Le serveur ne répond plus. Quittez DeckEdge puis relancez-le.", "The server is not responding. Quit DeckEdge and start it again." },
            { "Le serveur s'est arrêté au démarrage. Consultez le journal pour connaître la dépendance en cause.", "The server stopped during startup. Check the log to identify the failing dependency." },
            { "Le serveur n'est pas prêt après 20 secondes. Consultez le journal, puis réessayez.", "The server is not ready after 20 seconds. Check the log, then try again." },
            { "Pour afficher certaines températures et mesures matérielles, DeckEdge utilise le pilote PawnIO.\n\nL'installer maintenant ? Windows demandera votre accord. Vous pourrez aussi le faire plus tard depuis l'icône DeckEdge près de l'horloge.", "DeckEdge uses the PawnIO driver to show some temperatures and hardware readings.\n\nInstall it now? Windows will ask for your approval. You can also do this later from the DeckEdge tray icon." },
            { "Mesures matérielles", "Hardware measurements" },
            { "Impossible d'ouvrir le Studio\n\n", "Unable to open the Studio\n\n" },
            { "Le Studio n'a pas pu s'afficher. Cliquez sur Réessayer.", "The Studio could not be displayed. Click Retry." },
            { "Impossible d'ouvrir le sélecteur de couleur.", "Unable to open the color picker." },
            { "Le composant Microsoft WebView2 est nécessaire pour afficher le Studio.\n\nL'installer maintenant ? Une connexion Internet est nécessaire.", "Microsoft WebView2 is required to display the Studio.\n\nInstall it now? An Internet connection is required." },
            { "L'installation de WebView2 a échoué. Installez le Runtime depuis le site de Microsoft.", "WebView2 installation failed. Install the Runtime from Microsoft's website." },
            { "Installez Microsoft WebView2 Runtime depuis le site de Microsoft, puis relancez DeckEdge.", "Install Microsoft WebView2 Runtime from Microsoft's website, then restart DeckEdge." },
            { "Si l'installation du pilote a réussi, quittez puis relancez DeckEdge pour actualiser les capteurs.", "If the driver installation succeeded, quit and restart DeckEdge to refresh the sensors." },
            { "Python et les dépendances DeckEdge sont introuvables. Consultez le README et desktop.log.", "Python and the DeckEdge dependencies could not be found. See the README and desktop.log." },
            { "Quittez l'ancien serveur et relancez DeckEdge pour activer le moteur intégré.", "Quit the old server and restart DeckEdge to enable the integrated engine." },
            { "Le moteur intégré reçoit les mesures du PC.", "The integrated engine is receiving PC readings." },
            { "Le moteur intégré peut mettre quelques secondes à détecter les composants. Acceptez sa demande Windows pour accéder à tous les capteurs, notamment aux températures CPU.", "The integrated engine may take a few seconds to detect components. Accept its Windows prompt to access all sensors, including CPU temperatures." },
            { "● Serveur prêt · port {0}", "● Server ready · port {0}" },
            { "● Serveur indisponible", "● Server unavailable" },
            { "● Capteurs intégrés", "● Integrated sensors" },
            { "○ Capteurs intégrés · accès limité", "○ Integrated sensors · limited access" },
            { "○ Capteurs en attente — menu : Vérifier les capteurs", "○ Sensors waiting — menu: Check sensors" },
            { "prêt", "ready" },
            { "capteurs en attente", "sensors waiting" },
            { "serveur indisponible", "server unavailable" },
            { "DeckEdge — port du téléphone", "DeckEdge — phone port" },
            { "DeckEdge — capteurs", "DeckEdge — sensors" },
            { "Une autre copie de DeckEdge utilise déjà le port {0}. Quittez-la avant de relancer DeckEdge.", "Another DeckEdge copy is already using port {0}. Quit it before restarting DeckEdge." },
            { "Le port {0} est déjà utilisé. Choisissez un autre port avec DECKEDGE_PORT.", "Port {0} is already in use. Choose another port with DECKEDGE_PORT." },
            { "Aucun port local n'est disponible entre {0} et {1}.", "No local port is available between {0} and {1}." },
            { "Le port {0} est déjà utilisé. Arrêtez l'ancien serveur DeckEdge avant de réessayer.", "Port {0} is already in use. Stop the old DeckEdge server before trying again." },
            { "Le port {0} est utilisé pour cette session. Rouvrez « Connecter le téléphone » et rescannez le QR code si votre raccourci ne répond plus.", "Port {0} is used for this session. Open “Connect phone” again and rescan the QR code if your shortcut stops responding." },
            { "Connecter votre téléphone", "Connect your phone" },
            { "Ce PC · adresse permanente (recommandée)", "This PC · permanent address (recommended)" },
            { "Votre Deck, à portée de main.", "Your Deck, within reach." },
            { "Sur votre téléphone, ouvrez l'appareil photo et scannez le QR code. Le PC et le téléphone doivent être sur le même réseau privé.", "On your phone, open the camera and scan the QR code. The PC and phone must be on the same private network." },
            { "Réseau utilisé pour connecter le téléphone", "Network used to connect the phone" },
            { "QR code privé de connexion au pupitre", "Private deck connection QR code" },
            { "En attente du téléphone…", "Waiting for the phone…" },
            { "Copier le lien", "Copy link" },
            { "Lien copié", "Link copied" },
            { "Copie indisponible. Vous pouvez afficher le lien manuel.", "Copy unavailable. You can show the manual link." },
            { "Actualiser les réseaux", "Refresh networks" },
            { "Afficher le lien manuel", "Show manual link" },
            { "Lien privé complet du téléphone", "Full private phone link" },
            { "Une seule association suffit : ajoutez ensuite DeckEdge à l'écran d'accueil du téléphone. La clé de ce PC reste conservée aux prochains démarrages.", "One pairing is enough: then add DeckEdge to your phone's home screen. The PC key is kept for future launches." },
            { "Ce QR code et son lien donnent accès à votre pupitre : gardez-les privés. Le code est généré localement, sans service externe.", "This QR code and link grant access to your deck: keep them private. The code is generated locally without an external service." },
            { "Si la connexion échoue : vérifiez le même réseau Wi-Fi/Ethernet, évitez le Wi-Fi invité et choisissez une autre adresse ci-dessus si un VPN est actif. Le pare-feu doit autoriser DeckEdge sur le réseau privé.", "If the connection fails: check that both devices use the same Wi-Fi/Ethernet network, avoid guest Wi-Fi, and choose another address above if a VPN is active. The firewall must allow DeckEdge on the private network." },
            { "Aucun réseau local détecté. Connectez le PC au Wi-Fi ou à Ethernet, puis actualisez.", "No local network detected. Connect the PC to Wi-Fi or Ethernet, then refresh." },
            { "Réseaux indisponibles. Vérifiez la connexion du PC et actualisez.", "Networks unavailable. Check the PC connection and refresh." },
            { "QR code indisponible. Utilisez le lien manuel.", "QR code unavailable. Use the manual link." },
            { "Pupitre connecté · vous pouvez utiliser DeckEdge sur votre téléphone.", "Deck connected · you can use DeckEdge on your phone." },
            { "Le serveur ne répond pas encore. Gardez DeckEdge ouvert.", "The server is not responding yet. Keep DeckEdge open." },
            { "Serveur prêt · scannez le QR code pour connecter le téléphone.", "Server ready · scan the QR code to connect your phone." },
            { "Vérification du serveur indisponible.", "Server check unavailable." },
            { "DeckEdge — Pipette (Échap pour annuler)", "DeckEdge — Color picker (Esc to cancel)" },
            { "Le pixel sélectionné n'est pas accessible.", "The selected pixel is not accessible." },
            { "Fermer", "Close" },
        };

        private static readonly Dictionary<string, string> Translations = BuildTranslations();

        private static Dictionary<string, string> BuildTranslations()
        {
            var map = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var pair in English) map[Normalize(pair.Key)] = pair.Value;
            return map;
        }

        private static string Normalize(string value)
        {
            return String.IsNullOrEmpty(value) ? "" : value.Replace('\u2019', '\'').Replace('\u2018', '\'');
        }

        internal static void SetLanguage(string value)
        {
            language = value == "en" ? "en" : "fr";
        }

        internal static string T(string value)
        {
            if (!IsEnglish || String.IsNullOrEmpty(value)) return value;
            string translated;
            if (Translations.TryGetValue(Normalize(value), out translated)) return translated;
            string key = value.Trim();
            if (key.Length == 0) return value;
            if (!Translations.TryGetValue(Normalize(key), out translated)) return value;
            int start = value.IndexOf(key, StringComparison.Ordinal);
            return start < 0 ? translated : value.Substring(0, start) + translated + value.Substring(start + key.Length);
        }

        internal static string F(string value, params object[] arguments)
        {
            return String.Format(T(value), arguments);
        }

        private sealed class OriginalTexts
        {
            internal bool HasText;
            internal string Text;
            internal bool HasToolTip;
            internal string ToolTip;
            internal bool HasAccessibleName;
            internal string AccessibleName;
            internal bool HasAccessibleDescription;
            internal string AccessibleDescription;
        }

        private static readonly ConditionalWeakTable<object, OriginalTexts> Originals =
            new ConditionalWeakTable<object, OriginalTexts>();

        private static OriginalTexts Capture(object owner)
        {
            OriginalTexts record;
            if (!Originals.TryGetValue(owner, out record))
            {
                record = new OriginalTexts();
                Originals.Add(owner, record);
            }
            return record;
        }

        internal static void Translate(Control root)
        {
            if (root == null) return;
            var record = Capture(root);
            if (!record.HasText) { record.Text = root.Text; record.HasText = true; }
            root.Text = T(record.Text);
            if (!record.HasAccessibleName) { record.AccessibleName = root.AccessibleName; record.HasAccessibleName = true; }
            if (!String.IsNullOrEmpty(record.AccessibleName)) root.AccessibleName = T(record.AccessibleName);
            if (!record.HasAccessibleDescription) { record.AccessibleDescription = root.AccessibleDescription; record.HasAccessibleDescription = true; }
            if (!String.IsNullOrEmpty(record.AccessibleDescription)) root.AccessibleDescription = T(record.AccessibleDescription);
            if (root.ContextMenuStrip != null) TranslateItems(root.ContextMenuStrip.Items);
            ToolStrip strip = root as ToolStrip;
            if (strip != null) TranslateItems(strip.Items);
            foreach (Control child in root.Controls) Translate(child);
        }

        internal static void TranslateItems(ToolStripItemCollection items)
        {
            if (items == null) return;
            foreach (ToolStripItem item in items)
            {
                var record = Capture(item);
                if (!record.HasText) { record.Text = item.Text; record.HasText = true; }
                item.Text = T(record.Text);
                if (!record.HasToolTip) { record.ToolTip = item.ToolTipText; record.HasToolTip = true; }
                item.ToolTipText = T(record.ToolTip);
                if (!record.HasAccessibleName) { record.AccessibleName = item.AccessibleName; record.HasAccessibleName = true; }
                if (!String.IsNullOrEmpty(record.AccessibleName)) item.AccessibleName = T(record.AccessibleName);
                ToolStripDropDownItem drop = item as ToolStripDropDownItem;
                if (drop != null && drop.HasDropDownItems) TranslateItems(drop.DropDownItems);
            }
        }
    }
}
