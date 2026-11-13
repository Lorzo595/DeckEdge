# DeckEdge 0.1.1 — QR code et connexion durable au PC

Cette préversion simplifie la connexion du téléphone. Développé par **Lorzo595**,
avec l’aide de **ChatGPT**. Sources sous licence MIT.

## Nouveautés

- **QR code local** : dans le Studio, cliquer sur **Connecter le téléphone**, puis
  scanner avec l’appareil photo. Le QR code n’est envoyé à aucun service externe.
- **Adresse permanente propre au PC** : choisir **Ce PC · adresse permanente**.
  Le nom local reste stable lorsque l’adresse IP du PC change.
- **Association conservée** : la clé privée reste la même après redémarrage de
  DeckEdge. Ajouter la page à l’écran d’accueil ou aux favoris du téléphone pour
  retrouver le Deck sans recopier le lien ni scanner à chaque ouverture.
- **Adresse IP de secours**, sélection du réseau, actualisation et indicateur
  de connexion dans l’écran QR.
- **Aide mobile** pour garder le Deck sur son téléphone et page de reconnexion
  plus lisible si un ancien lien est utilisé.
- Reprise de la découverte locale au retour du réseau.
- Crédit **Lorzo595** et liens GitHub actualisés ; la mention ChatGPT est conservée.

## Télécharger

- **DeckEdge-0.1.1-Setup-x64.exe** : installation Windows classique.
- **DeckEdge-0.1.1-Portable-x64.zip** : extraire tout le dossier, puis lancer `DeckEdge.exe`.
- **DeckEdge-0.1.1-Source.zip** : sources publiques nettoyées.
- **SHA256SUMS.txt** : empreintes des fichiers de cette version.

Windows 10 (build 19041+) / Windows 11 **x64**. Python, LibreHardwareMonitor et le
générateur de QR code sont inclus. WebView2 est proposé s’il manque (Internet
nécessaire) ; PawnIO et les droits administrateur restent facultatifs pour les
mesures matérielles complètes. Aucun programme LibreHardwareMonitor séparé n’est requis.

## Connexion après mise à jour

1. Quitter complètement l’ancienne version depuis son icône près de l’horloge.
2. Installer 0.1.1, ou extraire le nouveau portable dans un nouveau dossier.
3. En portable, recopier l’ancien dossier `data` dans le nouveau pour conserver
   les profils et la clé du téléphone. L’installation classique conserve ses
   données dans `%LOCALAPPDATA%\DeckEdge`.
4. Ouvrir **Connecter le téléphone**, laisser **adresse permanente** sélectionné
   et scanner une fois le nouveau QR pour remplacer l’ancien favori basé sur l’IP.
5. Ajouter la page à l’écran d’accueil du téléphone ou aux favoris.

PC et téléphone doivent rester sur le même réseau privé, avec DeckEdge ouvert.
Certains réseaux invités, VPN ou routeurs bloquent mDNS/multicast : utiliser alors
l’adresse Wi-Fi/Ethernet de secours ; cette IP peut changer. L’effacement des
associations ou des données peut nécessiter un nouveau scan. Le QR code et le
raccourci contiennent une clé privée : ne pas les partager publiquement.

## Validation et limites

- QR code décodé automatiquement avec vérification du lien complet.
- Connexion confirmée sur le téléphone de test.
- Adresse permanente, WebSocket et retour sans nouveau QR vérifiés dans le navigateur.
- Clé et nom du PC conservés après redémarrage.
- 32 tests Python, tests des gestes tactiles et de la fidélité de l’aperçu mobile.

Cette version reste une **préversion de test**, pas encore la 1.0.0. Les exécutables
DeckEdge ne sont pas signés (avertissement SmartScreen possible). Le transport est
HTTP sur le réseau local : ne pas exposer DeckEdge sur Internet. La validation
sur plusieurs PC et sur un Windows vierge reste à compléter.

[Documentation](https://github.com/Lorzo595/DeckEdge#readme) ·
[Guide de démarrage](https://github.com/Lorzo595/DeckEdge/blob/main/docs/QUICKSTART.md) ·
[Signaler un problème](https://github.com/Lorzo595/DeckEdge/issues)
