# DeckEdge 0.1.0 — Première version de test publique

Transformez votre téléphone en pupitre de contrôle pour Windows, sans matériel
Stream Deck dédié. Développé par **Lorzo**, avec l’aide de **ChatGPT**. Sources MIT.

## Télécharger

- **DeckEdge-0.1.0-Setup-x64.exe** : installation classique, raccourcis Windows et désinstallation.
- **DeckEdge-0.1.0-Portable-x64.zip** : extraire toute l’archive puis lancer `DeckEdge/DeckEdge.exe`.
- **DeckEdge-0.1.0-Source.zip** : sources complètes propres, pour consulter ou modifier le projet.
- **SHA256SUMS.txt** : empreintes SHA256 de ces fichiers.

Windows 10 (build 19041+) ou Windows 11, **64 bits**. Python et le moteur
LibreHardwareMonitor sont inclus : aucun Python, Chrome ou programme LHM séparé
n’est nécessaire. Le téléchargement « Code → Download ZIP » contient seulement
les sources ; utilisez les fichiers de cette Release pour lancer l’application.

## Fonctionnalités

- Studio Windows dédié avec bibliothèque d’actions et recherche.
- Pupitre mobile dans le navigateur, aperçu portrait/paysage fidèle dans le Studio.
- Profils multiples ; touches déplaçables et redimensionnables.
- Raccourcis clavier, applications, fichiers, sites web et commandes multimédias.
- Volume Windows, sorties audio et volume des applications avec une session audio.
- Monitoring intégré avec 1 à 6 indicateurs personnalisables et seconde mesure facultative.
- Icônes, couleurs, pipette et états de bascule.
- Clic droit, duplication, annuler/rétablir et raccourcis d’édition.
- Intégration Discord RPC facultative avec configuration personnelle.
- Icône près de l’horloge, lancement au démarrage facultatif et section À propos.

## Installation et connexion

1. Lancer l’installateur ou extraire le portable dans un dossier accessible en écriture.
2. Ouvrir DeckEdge. WebView2 Runtime est proposé s’il manque ; son installation
   nécessite Internet. Le pilote signé PawnIO est proposé pour certaines mesures
   matérielles ; son installation et l’accès complet aux capteurs demandent un
   accord administrateur. On peut refuser et utiliser les mesures disponibles.
3. Configurer les touches dans le Studio puis cliquer sur **Enregistrer**.
4. Sur le même réseau privé que le PC, ouvrir sur le téléphone le lien complet
   fourni par **Connecter le téléphone**. Ce lien est privé : ne pas le publier.
5. Si Windows le demande, autoriser la connexion uniquement sur le réseau privé.

## Données et mises à jour

L’installation garde les données dans `%LOCALAPPDATA%\DeckEdge`. Le portable les
garde dans `data` à côté de l’exécutable. La désinstallation conserve les profils.
Pour mettre à jour le portable : quitter DeckEdge, extraire la nouvelle version dans
un nouveau dossier puis y recopier `data`. Ne pas mélanger les bibliothèques de versions différentes.
WebView2 et PawnIO restent des composants système, même en mode portable.

## Statut et limites

Cette version est une **préversion de test**, pas encore la 1.0.0.
Les tests locaux comprennent le lancement du portable déplacé avec un PATH sans
Python, l’installation, la désinstallation avec conservation des profils, les tests
Python et les vérifications du Studio. Les essais sur une machine Windows vierge
et sur plusieurs matériels restent à réaliser.

Les exécutables DeckEdge ne sont pas encore signés avec un certificat éditeur ;
SmartScreen peut afficher un avertissement. Les capteurs disponibles dépendent du
matériel et des droits Windows. Une application audio doit avoir créé une session
pour apparaître. Une seule copie peut utiliser le port TCP 5000 à la fois.
Le réseau local utilise HTTP : ne pas exposer DeckEdge sur Internet.

[Documentation complète](https://github.com/Lolomat595/DeckEdge#readme) ·
[Signaler un bug ou proposer une idée](https://github.com/Lolomat595/DeckEdge/issues) ·
[Guide de démarrage](https://github.com/Lolomat595/DeckEdge/blob/main/docs/QUICKSTART.md)

Avant de joindre un journal ou une capture, masquer les informations personnelles,
les identifiants Discord et les liens privés du téléphone. Ne jamais partager le
dossier de données complet. DeckEdge est indépendant d’Elgato et de Microsoft.
