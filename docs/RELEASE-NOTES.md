# DeckEdge 0.1.3 — Profils, sauvegardes et diagnostic

Préversion Windows x64 développée par **Lorzo595**, avec l’aide de **ChatGPT**. Merci à **xavco63** pour les contributions intégrées dans les PR #4 et #5.

## Nouveautés depuis 0.1.2

- Menu **Profils** : export JSON, import validé et annulable avant enregistrement.
- **Sauvegardes locales** horodatées : conservation des 20 dernières et restauration depuis le Studio.
- Sauvegarde de sécurité avant restauration ; si elle échoue, la restauration est annulée et la configuration actuelle est conservée.
- Protection contre un enregistrement et une restauration simultanés.
- Panneau **Diagnostic** avec rapport copiable ou téléchargeable et masquage des chemins personnels, clés et jetons connus.
- Port configurable et choix automatique en cas de conflit, mémorisé entre les lancements et conservé lors de l’application des paramètres. Le QR code et mDNS utilisent le port choisi.
- Écritures de configuration regroupées avec reprise après une erreur temporaire.
- Tests navigateur et C# intégrés aux contrôles GitHub ; normalisation des fins de ligne des sources.

Le QR code, l’adresse permanente du PC, le démarrage Windows et le maintien en éveil du PC et de son écran sont conservés.

## Télécharger

- **DeckEdge-0.1.3-Setup-x64.exe** : installation Windows classique.
- **DeckEdge-0.1.3-Portable-x64.zip** : extraire tout le dossier puis lancer DeckEdge.exe.
- **DeckEdge-0.1.3-Source.zip** : sources publiques nettoyées.
- **SHA256SUMS.txt** : empreintes des téléchargements.

Windows 10 build 19041+ / Windows 11 **x64**. Python et LibreHardwareMonitor sont inclus. WebView2 est proposé s’il manque ; Internet est alors nécessaire. L’accès complet aux capteurs reste facultatif et peut demander une autorisation administrateur.

## Mise à jour

1. Quitter complètement l’ancienne version depuis son icône près de l’horloge.
2. Installer la 0.1.3, ou extraire le nouveau portable dans un nouveau dossier.
3. En portable, recopier l’ancien dossier `data` dans le nouveau pour conserver profils, sauvegardes et clé du téléphone. L’installation classique conserve ses données dans `%LOCALAPPDATA%\DeckEdge`.
4. Si un conflit impose un changement de port et que le raccourci mobile ne répond plus, rouvrir **Connecter le téléphone** et scanner le nouveau QR. Le port choisi est ensuite mémorisé.

Les exports de profils peuvent contenir vos chemins et cibles d’actions : les relire avant partage. Relire également le diagnostic avant de le publier. Ne jamais partager le QR ou sa clé privée. PC et téléphone doivent rester sur le même réseau privé.

## Validation et limites

68 tests Python, huit tests Edge et test C# réussis sur les fonctionnalités fusionnées. Les contrôles GitHub compilent également les paquets Windows et vérifient les distributions. Les cas d’échec de sauvegarde et d’opérations concurrentes sont couverts par des tests de régression.

Cette version reste une **préversion**, pas la 1.0.0. Les exécutables sont non signés (avertissement SmartScreen possible). La validation sur plusieurs matériels, sur Windows vierge et après redémarrage complet de Windows reste à compléter. Les tests automatisés de commandes utilisent des simulations. Ne pas exposer le serveur HTTP sur Internet.

[Documentation](https://github.com/Lorzo595/DeckEdge#readme) · [Contributeurs](https://github.com/Lorzo595/DeckEdge#contributeurs) · [Signaler un problème](https://github.com/Lorzo595/DeckEdge/issues)
