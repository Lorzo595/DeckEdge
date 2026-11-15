/* FR/EN internationalization shared by the deck and the Studio. */
(() => {
  const STORAGE_KEY = 'deckedge.lang';
  const messages = {
    fr: {
      'language.switch': 'Passer en anglais',
      'language.button': 'EN',
      'language.label': 'Langue',
      'phone.install.title': 'Garder ce Deck sur mon téléphone',
      'phone.install.intro': 'Après ce premier scan, ajoutez cette page à l’écran d’accueil ou aux favoris. Vous retrouverez ce PC sans recopier le lien ni scanner à chaque démarrage.',
      'phone.install.ios': 'iPhone : Partager → Sur l’écran d’accueil. Android : menu du navigateur → Ajouter à l’écran d’accueil. Gardez DeckEdge ouvert sur le PC et utilisez le même réseau privé.',
      'phone.install.dismiss': 'Compris',
      'deck.monitoring': 'Mesures du PC',
      'deck.mute': 'Activer ou couper le son',
      'deck.muted': 'MUTÉ',
      'deck.output': 'SORTIE',
      'deck.master': 'MASTER',
      'deck.app': 'APP',
      'deck.steps': '{count} ÉTAPES',
      'deck.sensors.connected': 'Capteurs intégrés connectés',
      'deck.sensors.unavailable': 'Mesures indisponibles',
      'deck.volume': 'Volume',
      'deck.addPage': 'Ajouter une Page',
      'studio.editor.initial': 'Édition de l\'élément',
      'studio.editor.title': 'Édition #{index} ({label})',
      'studio.editor.customize': '{label} · Personnaliser',
      'studio.untitled': 'Sans nom',
      'studio.settings': 'Paramètres',
      'studio.test.button': '▶ Tester',
      'studio.test.running': 'Test en cours…',
      'studio.test.ok': 'Action prête',
      'studio.test.failed': 'Action incomplète',
      'studio.test.error': 'Test impossible : {detail}',
      'studio.test.step': 'Étape {step} · {message}',
      'studio.test.code.action.target.required': 'Une cible est requise.',
      'studio.test.code.action.key.ready': 'Touche reconnue : {detail}',
      'studio.test.code.action.key.unknown': 'Touche inconnue : {detail}',
      'studio.test.code.action.hotkey.ready': 'Raccourci reconnu : {detail}',
      'studio.test.code.action.hotkey.unknown': 'Raccourci inconnu : {detail}',
      'studio.test.code.action.launch.ready': 'Cible trouvée : {detail}',
      'studio.test.code.action.launch.uri': 'Adresse ou protocole valide : {detail}',
      'studio.test.code.action.launch.missing': 'Cible introuvable : {detail}',
      'studio.test.code.action.audio.ready': 'Sortie audio disponible : {detail}',
      'studio.test.code.action.audio.inactive': 'Aucune session audio active : {detail}. Lancez l’application puis actualisez les sorties.',
      'studio.test.code.action.audio.action_invalid': 'Action audio invalide : {detail}',
      'studio.test.code.action.sequence.ready': '{detail} étape(s) à tester.',
      'studio.test.code.action.sequence.empty': 'La séquence ne contient aucune étape.',
      'studio.test.code.action.condition.ready': 'Condition valide.',
      'studio.test.code.action.condition.button_missing': 'Touche de condition introuvable : {detail}',
      'studio.test.code.action.condition.app_required': 'Indiquez l’application de la condition.',
      'studio.test.code.action.condition.app_idle': 'L’application « {detail} » n’est pas lancée actuellement.',
      'studio.test.code.action.toggle.ready': 'Mode bascule valide.',
      'studio.test.code.action.type.unknown': 'Type d’action inconnu : {detail}',
      'studio.sequence.condition.label': 'Condition de l’étape',
      'studio.sequence.condition.always': 'Toujours',
      'studio.sequence.condition.button_on': 'Si la touche est active',
      'studio.sequence.condition.button_off': 'Si la touche est inactive',
      'studio.sequence.condition.app_running': 'Si l’application est lancée',
      'studio.sequence.condition.mic_muted': 'Si le micro est coupé',
      'studio.sequence.condition.mic_unmuted': 'Si le micro est actif',
      'studio.sequence.condition.button': 'Touche de condition',
      'studio.sequence.condition.chooseButton': 'Choisir une touche',
      'studio.sequence.condition.app': 'Application de la condition',
      'studio.sequence.condition.appPlaceholder': 'ex: spotify',
      'studio.sequence.condition.none': 'Aucune cible',
      'studio.icons.open': 'Bibliothèque',
      'studio.icons.title': 'Bibliothèque d’icônes',
      'studio.icons.search': 'Rechercher une icône…',
      'studio.icons.recent': 'Récentes',
      'studio.icons.empty': 'Aucune icône trouvée.',
      'studio.icons.insert': 'Insérer {icon}',
      'studio.icons.close': 'Fermer',
      'studio.icons.category.all': 'Toutes',
      'studio.icons.category.audio': 'Audio',
      'studio.icons.category.media': 'Médias',
      'studio.icons.category.apps': 'Applications',
      'studio.icons.category.system': 'Système',
      'studio.icons.category.gaming': 'Jeu',
      'studio.icons.category.symbols': 'Symboles',
      'studio.discord.title': '🎧 Liaison Native Discord API (RPC)',
      'studio.discord.link': '🚀 Lier mon compte Discord',
      'studio.appPicker.title': '🔍 Choisir une Application ou un Jeu',
      'studio.discord.step1': 'Ouvrez le <a href="https://discord.com/developers/applications" target="_blank" style="color:#38bdf8;text-decoration:underline;font-weight:600">Portail Développeur Discord ↗</a> et cliquez sur <b>"New Application"</b> (nom : <i>DeckEdge</i>).',
      'studio.discord.step2': 'Dans le menu de gauche, allez dans <b>OAuth2</b> &gt; <b>Redirects</b> et ajoutez : <code style="background:#020617;padding:2px 6px;border-radius:4px;color:#38bdf8">https://localhost/</code> puis enregistrez.',
      'studio.discord.step3': 'Copiez le <b>Client ID</b> (dans <i>General Information</i>) et le <b>Client Secret</b> (dans <i>OAuth2</i>) et collez-les ci-dessous :',
    },
    en: {
      'language.switch': 'Switch to French',
      'language.button': 'FR',
      'language.label': 'Language',
      'phone.install.title': 'Keep this Deck on your phone',
      'phone.install.intro': 'After this first scan, add this page to your home screen or bookmarks. You will find this PC again without copying the link or scanning at every startup.',
      'phone.install.ios': 'iPhone: Share → Add to Home Screen. Android: browser menu → Add to Home screen. Keep DeckEdge open on the PC and use the same private network.',
      'phone.install.dismiss': 'Got it',
      'deck.monitoring': 'PC measurements',
      'deck.mute': 'Mute or unmute',
      'deck.muted': 'MUTED',
      'deck.output': 'OUTPUT',
      'deck.master': 'MASTER',
      'deck.app': 'APP',
      'deck.steps': '{count} STEPS',
      'deck.sensors.connected': 'Integrated sensors connected',
      'deck.sensors.unavailable': 'Measurements unavailable',
      'deck.volume': 'Volume',
      'deck.addPage': 'Add a Page',
      'studio.editor.initial': 'Edit item',
      'studio.editor.title': 'Editing #{index} ({label})',
      'studio.editor.customize': '{label} · Customize',
      'studio.untitled': 'Untitled',
      'studio.settings': 'Settings',
      'studio.test.button': '▶ Test',
      'studio.test.running': 'Testing…',
      'studio.test.ok': 'Action ready',
      'studio.test.failed': 'Action incomplete',
      'studio.test.error': 'Test failed: {detail}',
      'studio.test.step': 'Step {step} · {message}',
      'studio.test.code.action.target.required': 'A target is required.',
      'studio.test.code.action.key.ready': 'Key recognized: {detail}',
      'studio.test.code.action.key.unknown': 'Unknown key: {detail}',
      'studio.test.code.action.hotkey.ready': 'Shortcut recognized: {detail}',
      'studio.test.code.action.hotkey.unknown': 'Unknown shortcut: {detail}',
      'studio.test.code.action.launch.ready': 'Target found: {detail}',
      'studio.test.code.action.launch.uri': 'Valid address or protocol: {detail}',
      'studio.test.code.action.launch.missing': 'Target not found: {detail}',
      'studio.test.code.action.audio.ready': 'Audio output available: {detail}',
      'studio.test.code.action.audio.inactive': 'No active audio session: {detail}. Start the application, then refresh the outputs.',
      'studio.test.code.action.audio.action_invalid': 'Invalid audio action: {detail}',
      'studio.test.code.action.sequence.ready': '{detail} step(s) to test.',
      'studio.test.code.action.sequence.empty': 'The sequence has no steps.',
      'studio.test.code.action.condition.ready': 'Condition is valid.',
      'studio.test.code.action.condition.button_missing': 'Condition key not found: {detail}',
      'studio.test.code.action.condition.app_required': 'Enter the application for the condition.',
      'studio.test.code.action.condition.app_idle': '“{detail}” is not running right now.',
      'studio.test.code.action.toggle.ready': 'Toggle mode is valid.',
      'studio.test.code.action.type.unknown': 'Unknown action type: {detail}',
      'studio.sequence.condition.label': 'Step condition',
      'studio.sequence.condition.always': 'Always',
      'studio.sequence.condition.button_on': 'When the key is active',
      'studio.sequence.condition.button_off': 'When the key is inactive',
      'studio.sequence.condition.app_running': 'When the application is running',
      'studio.sequence.condition.mic_muted': 'When the microphone is muted',
      'studio.sequence.condition.mic_unmuted': 'When the microphone is live',
      'studio.sequence.condition.button': 'Condition key',
      'studio.sequence.condition.chooseButton': 'Choose a key',
      'studio.sequence.condition.app': 'Condition application',
      'studio.sequence.condition.appPlaceholder': 'e.g. spotify',
      'studio.sequence.condition.none': 'No target',
      'studio.icons.open': 'Library',
      'studio.icons.title': 'Icon library',
      'studio.icons.search': 'Search for an icon…',
      'studio.icons.recent': 'Recent',
      'studio.icons.empty': 'No icon found.',
      'studio.icons.insert': 'Insert {icon}',
      'studio.icons.close': 'Close',
      'studio.icons.category.all': 'All',
      'studio.icons.category.audio': 'Audio',
      'studio.icons.category.media': 'Media',
      'studio.icons.category.apps': 'Apps',
      'studio.icons.category.system': 'System',
      'studio.icons.category.gaming': 'Gaming',
      'studio.icons.category.symbols': 'Symbols',
      'studio.discord.title': '🎧 Native Discord API link (RPC)',
      'studio.discord.link': '🚀 Link my Discord account',
      'studio.appPicker.title': '🔍 Choose an Application or Game',
      'studio.discord.step1': 'Open the <a href="https://discord.com/developers/applications" target="_blank" style="color:#38bdf8;text-decoration:underline;font-weight:600">Discord Developer Portal ↗</a> and click <b>"New Application"</b> (name: <i>DeckEdge</i>).',
      'studio.discord.step2': 'In the left menu, open <b>OAuth2</b> &gt; <b>Redirects</b> and add: <code style="background:#020617;padding:2px 6px;border-radius:4px;color:#38bdf8">https://localhost/</code> then save.',
      'studio.discord.step3': 'Copy the <b>Client ID</b> (from <i>General Information</i>) and the <b>Client Secret</b> (from <i>OAuth2</i>), then paste them below:',
    },
  };

  const legacyFrEn = {
    'Studio de contrôle': 'Control Studio',
    'Recharger': 'Reload',
    'Profils': 'Profiles',
    'Diagnostic': 'Diagnostics',
    'Annuler (Ctrl+Z)': 'Undo (Ctrl+Z)',
    'Rétablir (Ctrl+Y)': 'Redo (Ctrl+Y)',
    'Annuler la modification': 'Undo change',
    'Rétablir la modification': 'Redo change',
    '+ Ajouter une touche': '+ Add a key',
    'Paramètres': 'Settings',
    'Chargement…': 'Loading…',
    'Enregistrer': 'Save',
    'Enregistrer (Ctrl+S)': 'Save (Ctrl+S)',
    'Enregistrement…': 'Saving…',
    'Modifications non enregistrées': 'Unsaved changes',
    'À jour': 'Up to date',
    'Votre pupitre.': 'Your deck.',
    'Composez vos profils. Gardez vos commandes à portée de main.': 'Build your profiles. Keep your commands close at hand.',
    'DECK / ÉDITION': 'DECK / EDITING',
    'Monitoring du pupitre': 'Deck monitoring',
    'Détection des capteurs…': 'Detecting sensors…',
    'Choisissez de 1 à 6 indicateurs. Chaque indicateur peut afficher une deuxième mesure en dessous.': 'Choose 1 to 6 metrics. Each metric can show a second reading below it.',
    '+ Ajouter un indicateur': '+ Add a metric',
    'Actualiser les capteurs': 'Refresh sensors',
    'Appliquer avec « Enregistrer ».': 'Apply with “Save”.',
    'Page active :': 'Active page:',
    'Supprimer la page': 'Delete page',
    'Aperçu mobile du pupitre': 'Mobile deck preview',
    'Téléphone': 'Phone',
    'Standard · 390 × 844': 'Standard · 390 × 844',
    'Compact · 320 × 568': 'Compact · 320 × 568',
    'Grand · 430 × 932': 'Large · 430 × 932',
    'Zoom de l’aperçu': 'Preview zoom',
    'Ajuster': 'Fit',
    'Aperçu d’édition · aucune commande n’est exécutée. Les tailles et l’ordre sont ceux du mobile.': 'Editing preview · no command is executed. Sizes and order match the phone.',
    'Clic droit ou ⋯ pour les actions rapides · Glissez pour réorganiser · Ctrl+S pour enregistrer.': 'Right-click or ⋯ for quick actions · Drag to reorder · Ctrl+S to save.',
    'Votre Deck': 'Your Deck',
    'Sélectionnez une touche pour la personnaliser.': 'Select a key to customize it.',
    'Mes profils': 'My profiles',
    'Profils du Deck': 'Deck profiles',
    'Actions': 'Actions',
    'Ajoutez une action à votre Deck en un clic ou en la glissant sur l’aperçu.': 'Add an action to your deck with one click or by dragging it onto the preview.',
    'Rechercher une action': 'Search for an action',
    'Un Deck à votre image': 'A deck of your own',
    'Glissez les touches pour les réorganiser. Le clic droit permet de dupliquer, déplacer ou supprimer.': 'Drag keys to reorder them. Right-click to duplicate, move or delete.',
    'Aucune action trouvée. Essayez « volume » ou « clavier ».': 'No action found. Try “volume” or “keyboard”.',
    'Édition de l\'élément': 'Edit item',
    'Type d\'élément': 'Item type',
    '🎚️ Curseur Tactile (Slider de Volume)': '🎚️ Touch slider (volume)',
    'Touche simple ou multimédia (ex: playpause, volumeup)': 'Single or media key (e.g. playpause, volumeup)',
    'Raccourci combiné (ex: ctrl,shift,m ou win,d)': 'Key combination (e.g. ctrl,shift,m or win,d)',
    'Lancer une application / Fichier': 'Launch an application / file',
    'Incrément Volume App / Pas à pas (ex: spotify:+10)': 'App volume step (e.g. spotify:+10)',
    '🔗 Séquence d\'actions (plusieurs commandes)': '🔗 Action sequence (multiple commands)',
    'Largeur du widget': 'Widget width',
    'Automatique': 'Automatic',
    '¼ de ligne · 4 par ligne': '¼ row · 4 per row',
    '⅓ de ligne · 3 par ligne': '⅓ row · 3 per row',
    '½ ligne · 2 par ligne': '½ row · 2 per row',
    'Toute la largeur': 'Full width',
    'Hauteur du widget': 'Widget height',
    'Compacte': 'Compact',
    'Normale': 'Normal',
    'Grande · double hauteur': 'Tall · double height',
    'Réglages du Curseur de Volume': 'Volume slider settings',
    'Sortie Son ou Application à piloter': 'Output or application to control',
    '🔊 Général (Master Windows)': '🔊 General (Windows master)',
    'Recherche sur toutes les sorties audio. Une application doit avoir créé une session audio pour apparaître ; lancez un son puis actualisez si elle manque.': 'Searches all audio outputs. An application must have created an audio session to appear; play a sound and refresh if it is missing.',
    '🔄 Actualiser les sorties & apps': '🔄 Refresh outputs & apps',
    'Séquence d’actions': 'Action sequence',
    '+ Ajouter une étape': '+ Add a step',
    '10 étapes max · pause max 5 s': 'Up to 10 steps · max 5 s pause',
    'Les étapes s’exécutent dans l’ordre. La pause est appliquée après l’étape. Une étape en échec arrête la séquence.': 'Steps run in order. The pause is applied after each step. A failed step stops the sequence.',
    'Texte affiché': 'Display text',
    'Icône': 'Icon',
    'Couleur du bouton / jauge': 'Button / gauge color',
    'Code couleur du widget': 'Widget color code',
    'Prélever une couleur à l’écran': 'Pick a color on screen',
    'Pipette': 'Picker',
    'Bleu Cyan': 'Cyan blue',
    'Vert Spotify': 'Spotify green',
    'Violet Discord': 'Discord purple',
    'Orange': 'Orange',
    'Sombre Défaut': 'Default dark',
    'Commande / Cible brute': 'Command / raw target',
    '🔍 Choisir une Application, un Jeu ou un Outil...': '🔍 Choose an app, game or tool...',
    'ex: start discord:, master, app:spotify, ctrl,shift,m': 'e.g. start discord:, master, app:spotify, ctrl,shift,m',
    '🔄 Mode Bascule (Toggle ON/OFF)': '🔄 Toggle mode (ON/OFF)',
    '👁️ Tester état ON / OFF dans la grille': '👁️ Preview ON/OFF state in the grid',
    'Libellé si Actif': 'Active label',
    'Icône si Actif': 'Active icon',
    'Couleur si Actif': 'Active color',
    'Code couleur de l’état actif': 'Active state color code',
    'Rouge actif': 'Active red',
    'Vert actif': 'Active green',
    'Jaune actif': 'Active yellow',
    'Supprimer l\'élément': 'Delete item',
    'Taille et comportement': 'Size and behavior',
    'Options avancées': 'Advanced options',
    'Action': 'Action',
    'Choisir une application ou un outil…': 'Choose an application or tool…',
    'Commande, raccourci ou adresse': 'Command, shortcut or address',
    'Enregistrer un raccourci': 'Record a shortcut',
    'Appuyez sur votre combinaison · Échap pour annuler': 'Press your combination · Esc to cancel',
    'Cliquez sur « Enregistrer un raccourci », puis pressez les touches ensemble.': 'Click “Record a shortcut”, then press the keys together.',
    'Choisissez une application ou saisissez l’adresse complète d’un site.': 'Choose an application or enter the full address of a website.',
    'Choisissez une commande rapide ci-dessous.': 'Choose a quick command below.',
    'Choisissez une application et le pas de volume.': 'Choose an application and the volume step.',
    'Votre raccourci apparaîtra ici': 'Your shortcut will appear here',
    'Commande': 'Command',
    'Sans nom': 'Untitled',
    'Aucune étape. Ajoutez-en au moins une pour enregistrer cette séquence.': 'No step yet. Add at least one step to save this sequence.',
    'Pause après cette étape': 'Pause after this step',
    'Supprimer cette étape': 'Delete this step',
    'Une séquence est limitée à 10 étapes.': 'A sequence is limited to 10 steps.',
    'Touche': 'Key',
    'Raccourci': 'Shortcut',
    'Application': 'Application',
    'Audio': 'Audio',
    'Supprimer': 'Delete',
    'Voir': 'View',
    'Touche dupliquée.': 'Key duplicated.',
    'Profil dupliqué.': 'Profile duplicated.',
    'Profil supprimé.': 'Profile deleted.',
    'Touche supprimée.': 'Key deleted.',
    'Ajouter au profil': 'Add to profile',
    'Exporter les profils…': 'Export profiles…',
    'Importer des profils…': 'Import profiles…',
    'Sauvegardes locales…': 'Local backups…',
    'Touche / raccourci': 'Key / shortcut',
    'Curseur de volume': 'Volume slider',
    'Séquence d\'actions': 'Action sequence',
    'Modifier le nom': 'Rename',
    'Dupliquer': 'Duplicate',
    'Redimensionner…': 'Resize…',
    'Taille du widget': 'Widget size',
    'Petit · ¼ de ligne': 'Small · ¼ row',
    '⅓ de ligne': '⅓ row',
    '½ ligne': '½ row',
    'Grand widget': 'Large widget',
    'Déplacer vers un profil…': 'Move to a profile…',
    'Déplacer vers': 'Move to',
    'Ajouter une touche après': 'Add a key after',
    'Ajouter un curseur de volume': 'Add a volume slider',
    'Renommer': 'Rename',
    'Dupliquer le profil': 'Duplicate profile',
    'Ajouter un profil': 'Add a profile',
    'Supprimer le profil': 'Delete profile',
    'Ajouter une Page': 'Add a Page',
    'Donnez un nom à chaque indicateur de monitoring.': 'Give each monitoring metric a name.',
    'Configuration enregistrée et appliquée au pupitre.': 'Configuration saved and applied to the deck.',
    'Enregistrement impossible : le serveur ne répond pas. Vos modifications sont conservées.': 'Save failed: the server is not responding. Your changes are kept.',
    'Impossible de charger la configuration. Vérifiez que le serveur est actif.': 'Unable to load the configuration. Check that the server is running.',
    'Périphériques de sortie et applications audio détectés !': 'Audio outputs and applications detected!',
    'Chargement des applications et jeux installés...': 'Loading installed applications and games...',
    'Impossible de charger les applications.': 'Unable to load applications.',
    'Erreur réseau lors de la détection.': 'Network error while scanning.',
    'Aucune application ou jeu correspondant.': 'No matching application or game.',
    'Discord Détecté': 'Discord detected',
    '🎧 Discord Détecté': '🎧 Discord detected',
    'Avancé': 'Advanced',
    'Connecté': 'Connected',
    'Déconnecter': 'Disconnect',
    'Discord Connecté & Synchronisé': 'Discord connected & synced',
    'Le contrôle du micro et de la sourdine fonctionne désormais en arrière-plan à 100%, même en plein jeu sans que Discord soit au premier plan.': 'Microphone and deafen controls now work fully in the background, even in a full-screen game without Discord in front.',
    'État en direct & Test immédiat :': 'Live status & quick test:',
    'Micro Discord :': 'Discord microphone:',
    'Bascule Micro': 'Toggle mic',
    'Casque (Sourdine) :': 'Headset (deafen):',
    'Bascule Sourdine': 'Toggle deafen',
    'ACTIF': 'ACTIVE',
    'Pourquoi lier Discord ?': 'Why link Discord?',
    'Sans l\'API, couper le son ne coupe pas toujours le micro ou échoue si Discord n\'est pas au premier plan. Avec la liaison API locale officielle, vous pouvez couper votre micro d\'un clic depuis votre téléphone, même en plein écran de jeu !': 'Without the API, muting does not always mute the microphone or fails when Discord is not in the foreground. With the official local API link, you can mute your microphone with one click from your phone, even in a full-screen game!',
    'Guide rapide en 3 étapes (1 minute) :': 'Quick 3-step guide (1 minute):',
    'Discord DeckEdge': 'DeckEdge Discord',
    'Lier mon compte Discord': 'Link my Discord account',
    'Sauvegardes des profils': 'Profile backups',
    'Les 20 dernières sauvegardes locales sont conservées. Une sauvegarde est aussi créée avant chaque restauration.': 'The last 20 local backups are kept. A backup is also created before each restore.',
    'Créer une sauvegarde': 'Create a backup',
    'Fermer': 'Close',
    'Aucune sauvegarde locale pour le moment.': 'No local backup yet.',
    'Restaurer': 'Restore',
    'Sauvegarde créée.': 'Backup created.',
    'Sauvegarde restaurée.': 'Backup restored.',
    'Rapport de diagnostic copié.': 'Diagnostic report copied.',
    'Diagnostic DeckEdge': 'DeckEdge diagnostics',
    'Rapport local à joindre à un signalement. Les chemins personnels, la clé du téléphone et les adresses IP privées sont masqués. Vérifiez-le avant de le partager.': 'Local report to attach to a bug report. Personal paths, the phone key and private IP addresses are masked. Review it before sharing.',
    'Télécharger .txt': 'Download .txt',
    'Copier le rapport': 'Copy report',
    'Profils exportés.': 'Profiles exported.',
    'Profils importés. Cliquez sur « Enregistrer » pour les appliquer.': 'Profiles imported. Click “Save” to apply them.',
    'Tous': 'All',
    'Jeux Steam': 'Steam games',
    'Applications': 'Applications',
    'Outils Système': 'System tools',
    '⚙️ Outils Système': '⚙️ System tools',
    'Système': 'System',
    'Jeux': 'Games',
    'Rechercher une application ou un jeu (ex: Discord, Spotify, Steam, GTA...)': 'Search for an application or game (e.g. Discord, Spotify, Steam, GTA...)',
    'Choisir une Application, un Jeu ou un Outil...': 'Choose an app, game or tool...',
    'Aucune deuxième mesure': 'No secondary metric',
    'Sélection automatique': 'Automatic selection',
    'Capteur enregistré · actuellement absent': 'Saved sensor · currently unavailable',
    'Retirer l’indicateur': 'Remove metric',
    'Capteurs indisponibles · Réessayer avec Actualiser': 'Sensors unavailable · Retry with Refresh',
    'Charge CPU': 'CPU load',
    'Température CPU': 'CPU temperature',
    'Charge GPU': 'GPU load',
    'Température GPU': 'GPU temperature',
    'RAM utilisée': 'RAM used',
    'Master (Sortie)': 'Master (output)',
    'Casque HyperX': 'HyperX headset',
    'Discord Micro Mute (API)': 'Discord mic mute (API)',
    'Discord Sourdine (API)': 'Discord deafen (API)',
    'Micro Windows Mute': 'Windows microphone mute',
    'Spotify Mute': 'Spotify mute',
    'Master Mute': 'Master mute',
    'Master +5%': 'Master +5%',
    'Master -5%': 'Master -5%',
    'Discord +10%': 'Discord +10%',
    'Discord -10%': 'Discord -10%',
    'Spotify +10%': 'Spotify +10%',
    'Spotify -10%': 'Spotify -10%',
    'Vol + (OSD)': 'Vol + (OSD)',
    'Vol - (OSD)': 'Vol - (OSD)',
    'Play/Pause': 'Play/Pause',
    'Suivant': 'Next',
    'Précédent': 'Previous',
    'Mute Son (OSD)': 'Mute sound (OSD)',
    'Discord Mute (Ctrl+Shift+M)': 'Discord mute (Ctrl+Shift+M)',
    'Discord Sourdine (Ctrl+Shift+D)': 'Discord deafen (Ctrl+Shift+D)',
    'Bureau (Win+D)': 'Desktop (Win+D)',
    'Capture Écran (Win+Shift+S)': 'Screenshot (Win+Shift+S)',
    'Game Bar Xbox (Win+G)': 'Xbox Game Bar (Win+G)',
    'Overlay Steam / Jeu (Shift+Tab)': 'Steam / game overlay (Shift+Tab)',
    'Fermer Fenêtre (Alt+F4)': 'Close window (Alt+F4)',
    'Gestionnaire Tâches (Ctrl+Shift+Esc)': 'Task Manager (Ctrl+Shift+Esc)',
    'OBS Rec (Ctrl+F9)': 'OBS recording (Ctrl+F9)',
    'YouTube Music': 'YouTube Music',
    'Ouvrir Discord': 'Open Discord',
    'Ouvrir Spotify': 'Open Spotify',
    'Ouvrir Steam': 'Open Steam',
    'Calculatrice': 'Calculator',
    'Task Manager': 'Task Manager',
    'Explorateur Fichiers': 'File Explorer',
    'Navigateur Chrome': 'Chrome browser',
    'Game Bar Xbox': 'Xbox Game Bar',
    'Séquence': 'Sequence',
    'Enchaîner plusieurs actions': 'Chain several actions',
    'Mon application': 'My application',
    'Mon site': 'My site',
    'Mon raccourci': 'My shortcut',
    'Bureau': 'Desktop',
    'Contrôler la musique': 'Control music',
    'Passer au morceau suivant': 'Skip to the next track',
    'Activer ou couper le son du PC': 'Mute or unmute the PC',
    'Application, jeu ou fichier': 'Application, game or file',
    'Accéder à une adresse web': 'Open a web address',
    'Combiner plusieurs touches': 'Combine several keys',
    'Retrouver le bureau Windows': 'Return to the Windows desktop',
    'Régler le son d’une application': 'Adjust an application’s volume',
    'Lecture / Pause': 'Play / Pause',
    'Piste suivante': 'Next track',
    'Couper le son': 'Mute',
    'Ouvrir une application': 'Open an application',
    'Ouvrir un site': 'Open a website',
    'Raccourci clavier': 'Keyboard shortcut',
    'Afficher le bureau': 'Show the desktop',
    'Navigateur Windows': 'Windows browser',
    'Téléphone Android': 'Android phone',
    'Téléphone': 'Phone',
    'Volume': 'Volume',
    'Musique': 'Music',
  };

  const legacyPatterns = [
    [/^Édition #(\d+) \((.*)\)$/, match => `Editing #${match[1]} (${match[2]})`],
    [/^(.*) · Personnaliser$/, match => `${match[1]} · Customize`],
    [/^Touche déplacée vers « (.*) »\.$/, match => `Key moved to “${match[1]}”.`],
    [/^Supprimer l['’]étape (\d+)$/, match => `Delete step ${match[1]}`],
    [/^(\d+) étapes$/, match => `${match[1]} steps`],
    [/^(\d+) capteurs · Accès complet$/, match => `${match[1]} sensors · Full access`],
    [/^(\d+) capteurs · Accès limité$/, match => `${match[1]} sensors · Limited access`],
    [/^Enregistrement refusé : (.*)$/, match => `Save refused: ${match[1]}`],
    [/^Import impossible : (.*)$/, match => `Import failed: ${match[1]}`],
    [/^Sauvegarde impossible : (.*)$/, match => `Backup failed: ${match[1]}`],
    [/^Restauration impossible : (.*)$/, match => `Restore failed: ${match[1]}`],
    [/^Impossible de charger les sauvegardes : (.*)$/, match => `Unable to load backups: ${match[1]}`],
    [/^Ajouter : (.*)$/, match => `Add: ${match[1]}`],
    [/^Tous \($/, () => 'All ('],
    [/^🎮 Jeux Steam \($/, () => '🎮 Steam games ('],
    [/^💬 Applications \($/, () => '💬 Applications ('],
  ];

  const normalizeKey = value => String(value)
    .replace(/[’‘]/g, "'")
    .replace(/…/g, '...')
    .replace(/\s+/g, ' ')
    .trim();

  const legacyLookup = new Map(Object.entries(legacyFrEn).map(([key, value]) => [normalizeKey(key), value]));

  const supported = Object.keys(messages);

  const listeners = [];

  function normalize(value) {
    const language = String(value || '').toLowerCase();
    return language.startsWith('fr') ? 'fr' : 'en';
  }

  function detect() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (supported.includes(saved)) return saved;
    } catch {}
    return normalize(navigator.language || navigator.userLanguage || 'en');
  }

  let language = detect();

  function persistLanguage() {
    try { localStorage.setItem(STORAGE_KEY, language); } catch {}
    try { document.cookie = `deckedge_lang=${language}; Path=/; SameSite=Lax; Max-Age=31536000`; } catch {}
  }

  // Optional ?lang=en / ?lang=fr for links and deterministic tests.
  try {
    const requested = new URL(location.href).searchParams.get('lang');
    if (supported.includes(requested)) {
      language = requested;
      persistLanguage();
      const url = new URL(location.href);
      url.searchParams.delete('lang');
      history.replaceState(null, '', url.pathname + url.search + url.hash);
    }
  } catch {}
  persistLanguage();

  function t(key, values = {}) {
    const table = messages[language] || messages.en;
    const fallback = messages.en;
    let text = table[key] ?? fallback[key] ?? key;
    return String(text).replace(/\{(\w+)\}/g, (match, name) =>
      Object.prototype.hasOwnProperty.call(values, name) ? String(values[name]) : match
    );
  }

  function apply(root = document) {
    document.documentElement.lang = language;
    root.querySelectorAll('[data-i18n]').forEach(element => {
      element.textContent = t(element.dataset.i18n);
    });
    root.querySelectorAll('[data-i18n-html]').forEach(element => {
      element.innerHTML = t(element.dataset.i18nHtml);
    });
    root.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
      element.setAttribute('placeholder', t(element.dataset.i18nPlaceholder));
    });
    root.querySelectorAll('[data-i18n-title]').forEach(element => {
      element.setAttribute('title', t(element.dataset.i18nTitle));
    });
    root.querySelectorAll('[data-i18n-aria-label]').forEach(element => {
      element.setAttribute('aria-label', t(element.dataset.i18nAriaLabel));
    });
  }

  const LEGACY_SKIP = [
    'script', 'style', 'noscript', 'textarea', 'pre', 'code',
    '#diagnostics-output', '#discord-user-display', '#editor-title',
    '.preview-btn', '.page-tab', '.phone-tab', '.preview-monitoring',
    '.preview-phone-pages', '.backup-row', '[data-i18n]', '[data-i18n-html]'
  ].join(',');

  let legacyEnabled = false;
  let legacyObserver = null;
  let legacyDepth = 0;
  let legacyDialogsInstalled = false;
  const legacyTextRecords = new Map();
  const legacyAttrRecords = new Map();

  function translateLegacyString(value) {
    const source = String(value ?? '');
    const key = normalizeKey(source);
    if (!key) return source;
    let translated = legacyLookup.get(key);
    if (!translated) {
      for (const [pattern, replacer] of legacyPatterns) {
        const match = key.match(pattern);
        if (match) { translated = replacer(match); break; }
      }
    }
    if (!translated) return source;
    const trimmed = source.trim();
    return trimmed ? source.replace(trimmed, translated) : source;
  }

  function legacySkipped(element) {
    return !element || Boolean(element.closest(LEGACY_SKIP));
  }

  function translateLegacyTextNode(node) {
    if (!node || node.nodeType !== Node.TEXT_NODE || legacySkipped(node.parentElement)) return;
    const record = legacyTextRecords.get(node);
    const current = node.nodeValue;
    if (record && current === record.translated) return;
    const source = record && current === record.source ? record.source : current;
    const translated = translateLegacyString(source);
    if (translated !== source) {
      legacyTextRecords.set(node, {source, translated});
      node.nodeValue = translated;
    } else if (record) {
      legacyTextRecords.delete(node);
    }
  }

  function translateLegacyAttribute(element, name) {
    if (!element || element.nodeType !== Node.ELEMENT_NODE || legacySkipped(element)) return;
    let records = legacyAttrRecords.get(element);
    if (!records) { records = new Map(); legacyAttrRecords.set(element, records); }
    const record = records.get(name);
    const current = element.getAttribute(name);
    if (current === null) return;
    if (record && current === record.translated) return;
    const source = record && current === record.source ? record.source : current;
    const translated = translateLegacyString(source);
    if (translated !== source) {
      records.set(name, {source, translated});
      element.setAttribute(name, translated);
    } else if (record) {
      records.delete(name);
    }
  }

  function translateLegacyTree(root) {
    if (!legacyEnabled || language !== 'en' || !root) return;
    legacyDepth++;
    try {
      if (root.nodeType === Node.TEXT_NODE) translateLegacyTextNode(root);
      if (root.nodeType !== Node.ELEMENT_NODE) return;
      translateLegacyAttribute(root, 'title');
      translateLegacyAttribute(root, 'placeholder');
      translateLegacyAttribute(root, 'aria-label');
      root.querySelectorAll('[title],[placeholder],[aria-label]').forEach(element => {
        translateLegacyAttribute(element, 'title');
        translateLegacyAttribute(element, 'placeholder');
        translateLegacyAttribute(element, 'aria-label');
      });
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
        acceptNode(node) {
          return legacySkipped(node.parentElement) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
        }
      });
      while (walker.nextNode()) translateLegacyTextNode(walker.currentNode);
    } finally {
      legacyDepth--;
    }
  }

  function restoreLegacy() {
    legacyDepth++;
    try {
      legacyTextRecords.forEach((record, node) => { node.nodeValue = record.source; });
      legacyAttrRecords.forEach((records, element) => {
        records.forEach((record, name) => element.setAttribute(name, record.source));
      });
    } finally {
      legacyTextRecords.clear();
      legacyAttrRecords.clear();
      legacyDepth--;
    }
  }

  function startLegacyObserver() {
    if (legacyObserver || !document.body) return;
    legacyObserver = new MutationObserver(mutations => {
      if (legacyDepth > 0 || language !== 'en') return;
      legacyDepth++;
      try {
        mutations.forEach(mutation => {
          if (mutation.type === 'characterData') {
            translateLegacyTextNode(mutation.target);
          } else if (mutation.type === 'childList') {
            mutation.addedNodes.forEach(node => {
              if (node.nodeType === Node.TEXT_NODE) translateLegacyTextNode(node);
              else if (node.nodeType === Node.ELEMENT_NODE) translateLegacyTree(node);
            });
          } else if (mutation.type === 'attributes' && mutation.attributeName) {
            translateLegacyAttribute(mutation.target, mutation.attributeName);
          }
        });
      } finally {
        legacyDepth--;
      }
    });
    legacyObserver.observe(document.body, {
      subtree: true, childList: true, characterData: true,
      attributes: true, attributeFilter: ['title', 'placeholder', 'aria-label']
    });
  }

  function stopLegacyObserver() {
    if (legacyObserver) {
      legacyObserver.disconnect();
      legacyObserver = null;
    }
  }

  function installLegacyDialogs() {
    if (legacyDialogsInstalled) return;
    const nativeConfirm = window.confirm.bind(window);
    const nativeAlert = window.alert.bind(window);
    const nativePrompt = window.prompt.bind(window);
    const maybeTranslate = message => language === 'en' ? translateLegacyString(message) : String(message);
    window.confirm = message => nativeConfirm(maybeTranslate(message));
    window.alert = message => nativeAlert(maybeTranslate(message));
    window.prompt = (message, defaultValue) => nativePrompt(maybeTranslate(message), defaultValue);
    legacyDialogsInstalled = true;
  }

  function enableLegacy() {
    legacyEnabled = true;
    installLegacyDialogs();
    if (language === 'en') {
      translateLegacyTree(document.body);
      startLegacyObserver();
    }
  }

  function setLanguage(next) {
    const value = supported.includes(next) ? next : 'en';
    if (value === language) return;
    stopLegacyObserver();
    restoreLegacy();
    language = value;
    persistLanguage();
    apply();
    if (legacyEnabled && language === 'en') {
      translateLegacyTree(document.body);
      startLegacyObserver();
    }
    listeners.forEach(listener => {
      try { listener(language); } catch (error) { console.error(error); }
    });
  }

  function toggleLanguage() {
    setLanguage(language === 'fr' ? 'en' : 'fr');
  }

  function onChange(listener) {
    if (typeof listener === 'function') listeners.push(listener);
  }

  apply();
  window.addEventListener('DOMContentLoaded', () => apply());
  window.I18n = {
    get lang() { return language; },
    t,
    apply,
    setLanguage,
    toggleLanguage,
    onChange,
    enableLegacy,
    translateString: translateLegacyString,
  };
})();
