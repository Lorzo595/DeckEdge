# Démarrer avec DeckEdge

Développé par Lorzo, avec l’aide de ChatGPT. Code source sous licence MIT.

## Installation
Lancer Setup-x64.exe, choisir le dossier et terminer l’assistant. Un raccourci
est ajouté au menu Démarrer ; le raccourci du Bureau est facultatif. La suppression
passe par les applications installées de Windows. Les profils restent conservés.

## Portable
Extraire l’archive entière dans un dossier personnel, puis lancer DeckEdge.exe.
Conserver ensemble l’exécutable, les bibliothèques, runtime et portable.flag.
Les profils sont créés dans data. Déplacer le dossier entier pour emporter le Deck.
WebView2 est un composant Windows partagé : si absent, DeckEdge propose de l’installer.
Le pilote matériel PawnIO est lui aussi un prérequis système facultatif et ne
peut pas être rendu portable. Sans lui, certaines mesures sont indisponibles.

## Configurer
Choisir un profil à gauche. Ajouter une action depuis la bibliothèque à droite,
par clic ou glisser-déposer sur l’aperçu. Cliquer sur une touche de l’aperçu pour
modifier ses réglages en dessous. Taille et comportement contient la largeur,
la hauteur et le mode bascule. Les options techniques restent repliées.
Un raccourci clavier peut être enregistré en pressant les touches ensemble.
Dans Paramètres, la section À propos de DeckEdge indique la version installée,
le développeur, la licence MIT et les composants principaux.

L’aperçu n’exécute aucune commande. Enregistrer applique les changements au téléphone.
Le clic droit permet de dupliquer, déplacer et supprimer. Ctrl+Z annule.
Les profils existants s’ouvrent sur Principal lorsqu’il existe.

## Téléphone
Le téléphone et le PC doivent être sur le même réseau privé. Utiliser le lien
complet de Connecter le téléphone : il contient une clé privée. Ne pas le partager
publiquement. Si un ancien favori ne fonctionne plus, recopier le nouveau lien.
Glisser verticalement fait défiler ; glisser horizontalement règle un curseur.

## Capteurs et audio
Accepter l’accès administrateur du moteur de capteurs pour les mesures complètes.
Si des températures manquent sur un nouveau PC, installer PawnIO depuis le menu
DeckEdge près de l’horloge, puis quitter et relancer DeckEdge. Le pilote d’origine
est signé et fourni avec le logiciel ; LibreHardwareMonitor ne doit pas être lancé.
Une application audio apparaît après avoir créé une session : jouer un son puis
actualiser les sorties et applications dans les réglages d’un curseur de volume.

## Dépannage
- Studio absent : relancer depuis l’icône près de l’horloge.
- Port 5000 occupé : quitter l’autre copie de DeckEdge ou l’ancien serveur.
- Téléphone inaccessible : même réseau, lien privé complet, pare-feu réseau privé,
  pas d’isolation Wi-Fi des clients. Ne pas ouvrir de port sur le routeur.
- Studio blanc : installer/réparer Microsoft WebView2 Runtime depuis Microsoft.
- Logs : menu DeckEdge → Voir le journal / Ouvrir les données.
- Quitter complètement avant de déplacer ou remplacer une version portable.
