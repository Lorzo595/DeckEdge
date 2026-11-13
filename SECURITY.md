# Sécurité et données locales

DeckEdge exécute sur votre PC les raccourcis et applications que vous configurez.
Utilisez-le sur un réseau privé de confiance. Il ne doit pas être exposé sur Internet
ou placé derrière une redirection de port. Le transport local est HTTP, sans TLS.

Le Studio et les modifications de configuration ne sont accessibles que depuis le PC.
Le téléphone doit utiliser le lien complet fourni dans « Connecter le téléphone » :
ce lien contient une clé d’accès privée. Ne le publiez pas. Le navigateur mémorise
l’association dans un cookie. Pour révoquer tous les téléphones, quittez DeckEdge,
supprimez `.phone-key` dans le dossier de données et redémarrez, puis reconnectez-les.
Une origine web externe ne peut pas utiliser le serveur ni ses WebSockets.

Le nom permanent `.local` est dérivé d’un identifiant du PC, sans publier cet
identifiant brut. La découverte mDNS annonce seulement le nom et le port du service,
jamais la clé privée. Le QR code est généré localement. Le manifeste de raccourci
est réservé aux appareils associés, n’est pas mis en cache et conserve le lien
privé pour retrouver le Deck après redémarrage. Ne partagez pas ce raccourci.

Les données sont stockées dans `%LOCALAPPDATA%\DeckEdge` pour l’installation,
ou `data` à côté de DeckEdge.exe en portable. Les jetons Discord sont locaux ;
ils ne doivent jamais être ajoutés à GitHub, aux captures ou aux signalements.
La désinstallation conserve les profils. Supprimez volontairement ce dossier
après désinstallation si vous souhaitez aussi effacer vos données.

Pour signaler une vulnérabilité, utilisez l’onglet Security du dépôt GitHub et
« Report a vulnerability » lorsqu’il est activé. Ne publiez aucun secret dans
une issue publique. Si ce canal n’est pas activé, contactez le propriétaire du
dépôt avant de publier les détails exploitables.
