# DeckEdge

Votre téléphone devient un pupitre de contrôle pour Windows : raccourcis,
applications, musique, volume par application et monitoring matériel.
Le Studio Windows permet de tout organiser avec un aperçu mobile, une bibliothèque
d’actions et des réglages simples. Aucun Stream Deck physique n’est nécessaire.

**Windows 10 (2004+) / Windows 11 · x64 · version 0.1.2 · licence MIT**

Développé par **Lorzo595**, avec l’aide de **ChatGPT**.

> **Version de test publique.** DeckEdge 0.1.2 fonctionne et a été testé
> sur le poste de développement, mais la validation sur plusieurs PC et les retours
> utilisateurs restent nécessaires avant une version 1.0.0.

[Télécharger la version 0.1.2](https://github.com/Lorzo595/DeckEdge/releases/tag/v0.1.2)
· [Signaler un problème](https://github.com/Lorzo595/DeckEdge/issues)
· [Guide de démarrage](docs/QUICKSTART.md)

## Fonctionnalités

| Domaine | Ce que permet DeckEdge |
| --- | --- |
| Studio Windows | Fenêtre dédiée, icône près de l’horloge, réglages locaux et lancement au démarrage facultatif |
| Pupitre mobile | Interface dans le navigateur du téléphone, en portrait ou paysage, sur le même réseau privé que le PC |
| Connexion au PC | Premier scan par QR code local, clé conservée et adresse permanente propre au PC pour les ouvertures suivantes |
| Profils | Plusieurs pages de commandes, ajout, renommage, duplication et déplacement de touches |
| Organisation | Aperçu de téléphone, glisser-déposer et widgets de largeur et hauteur réglables |
| Actions | Raccourcis clavier, touches multimédias, lancement d’applications, fichiers et sites web |
| Audio | Volume Windows, sorties audio et applications ayant une session audio active, avec curseurs et sourdine |
| Monitoring | Moteur LibreHardwareMonitor intégré et choix de 1 à 6 indicateurs, avec une seconde mesure facultative |
| Personnalisation | Nom, icône, couleurs, pipette et états actif/inactif pour les touches à bascule |
| Édition | Bibliothèque avec recherche, clic droit, duplication, annuler/rétablir et raccourcis clavier |
| Discord | Intégration RPC facultative pour le micro et la sourdine, nécessitant une configuration Discord personnelle |

Le téléphone n’a pas d’application à installer et aucun compte DeckEdge n’est
nécessaire. Les commandes s’exécutent sur le PC ; le téléphone sert de télécommande.
Le logiciel ne nécessite aucun abonnement et son code est disponible sous MIT.

## Télécharger

Dans la [Release 0.1.2](https://github.com/Lorzo595/DeckEdge/releases/tag/v0.1.2), choisir :

| Fichier | Usage |
| --- | --- |
| `DeckEdge-0.1.2-Setup-x64.exe` | Installation classique, raccourcis et désinstallation Windows |
| `DeckEdge-0.1.2-Portable-x64.zip` | Décompresser, puis lancer `DeckEdge/DeckEdge.exe` ; tout reste dans ce dossier |
| `DeckEdge-0.1.2-Source.zip` | Sources propres à publier, étudier ou modifier |
| `SHA256SUMS.txt` | Empreintes des fichiers de cette version |

Python et le moteur LibreHardwareMonitor sont inclus. Il n’est pas nécessaire
d’installer Python, Chrome ou l’application LibreHardwareMonitor.
Microsoft WebView2 Runtime est nécessaire ; DeckEdge propose son installation
s’il manque (connexion Internet nécessaire). Le pilote PawnIO est proposé pour
certaines températures et mesures matérielles ; il nécessite un accord administrateur.
Le Studio fonctionne sans droits administrateur, avec des mesures limitées si
l’accès matériel complet est refusé.

### Installation classique

1. Télécharger `DeckEdge-0.1.2-Setup-x64.exe` depuis la Release.
2. Suivre l’assistant. L’installation se fait pour l’utilisateur courant, avec
   un raccourci dans le menu Démarrer et un raccourci Bureau facultatif.
3. Ouvrir DeckEdge. Accepter l’installation de WebView2 s’il manque et choisir
   si l’accès matériel complet est souhaité.
4. La désinstallation passe par les applications installées de Windows ; les
   profils sont conservés dans le dossier de données de l’utilisateur.

### Version portable

1. Télécharger `DeckEdge-0.1.2-Portable-x64.zip` et extraire **toute** l’archive.
2. Ouvrir le dossier `DeckEdge`, puis lancer `DeckEdge.exe`.
3. Conserver ensemble `runtime`, les bibliothèques et `portable.flag`. Les données
   sont créées dans `data` ; déplacer le dossier entier pour emporter le Deck.

WebView2 et le pilote matériel PawnIO restent des composants système : le mode
portable concerne DeckEdge et ses données, pas l’installation de ces prérequis.
Il peut fonctionner hors ligne une fois les prérequis présents, sauf les actions
qui ouvrent des services en ligne. Ne pas télécharger le ZIP « Code » de GitHub
pour installer l’app : ce ZIP contient les sources et aucun exécutable prêt à lancer.

Les exécutables de cette première version ne sont pas signés avec un certificat
éditeur DeckEdge. Windows peut afficher un avertissement SmartScreen. Distribuez
uniquement les fichiers que vous avez construits ou téléchargés depuis la Release
originale, et vérifiez leur empreinte en cas de doute.

## Premiers pas

1. Installer DeckEdge ou extraire **tout** le dossier de l’archive portable dans
   un emplacement où vous pouvez écrire. Lancer `DeckEdge.exe`.
2. Dans le Studio, choisir un profil, ajouter une action depuis la bibliothèque,
   puis sélectionner la touche pour régler son nom, son icône et sa couleur.
3. Cliquer sur **Enregistrer**. Le clic droit, le glisser-déposer, Ctrl+Z et Ctrl+S
   permettent de travailler plus rapidement.
4. Connecter le téléphone au même réseau privé que le PC. Dans DeckEdge,
   **Connecter le téléphone** affiche un QR code privé à scanner. Choisir
   **Ce PC · adresse permanente**, puis ajouter la page ouverte à l’écran
   d’accueil du téléphone ou aux favoris : un nouveau scan n’est pas nécessaire
   à chaque démarrage. Le lien peut toujours être copié en secours.
5. Si le pare-feu Windows le demande, autoriser DeckEdge/Python sur le réseau
   **privé uniquement**. Le serveur utilise le port TCP 5000.

Fermer la fenêtre conserve par défaut DeckEdge près de l’horloge. Le menu de
cette icône permet de rouvrir le Studio, quitter complètement, voir les journaux
ou ouvrir les données. **Paramètres** permet notamment le lancement au démarrage.
La section **À propos de DeckEdge** y affiche la version, le développeur, la
licence et les crédits des principaux composants, avec accès au texte de licence.
Une seule copie de DeckEdge peut utiliser le port 5000 à la fois : quittez la
version installée avant d’utiliser une copie portable, et inversement.

[Guide de démarrage](docs/QUICKSTART.md) · [Construction](docs/BUILD.md) ·
[Publication GitHub](docs/RELEASE.md) · [Sécurité](SECURITY.md)

L’adresse permanente utilise la découverte locale mDNS (`.local`) et reste propre
au PC même si son adresse IP change. La clé d’association reste dans les données
de DeckEdge : ni un redémarrage ni le changement de pseudo GitHub ne la modifient.
Sur un réseau bloquant le multicast, choisir l’adresse Wi-Fi/Ethernet de secours
dans l’écran QR ; cette adresse IP peut changer. Effacer les données de DeckEdge
ou supprimer le raccourci et l’association du navigateur peut nécessiter un nouveau scan.

## Vos données

- Version installée : `%LOCALAPPDATA%\DeckEdge`.
- Version portable : `data` à côté de `DeckEdge.exe`.
- Développement depuis les sources : dossier du projet, sauf si
  `DECKEDGE_DATA_DIR` désigne un autre emplacement.

Les profils, réglages, clé du téléphone et identifiants Discord ne sont jamais
inclus dans les distributions produites par les scripts de construction.
La désinstallation conserve les profils. Pour migrer, quittez les deux versions
puis copiez vos fichiers de données dans le nouveau dossier ; reconnectez le
compte Discord si nécessaire. Sauvegardez le dossier avant une mise à jour.

Pour mettre à jour une version portable : extraire la nouvelle version dans un
nouveau dossier, puis y recopier l’ancien dossier `data`. Ne mélangez pas les
bibliothèques de versions différentes. Conservez `portable.flag` près de l’exécutable.
Le démarrage automatique d’une copie portable doit être réactivé si vous la déplacez.

## Développer

Windows x64, Python 3.14 et .NET Framework 4.8 sont recommandés.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m unittest discover -s tests -t . -p "test_*.py"
powershell -ExecutionPolicy Bypass -File desktop\build.ps1
```

`desktop/build.ps1` récupère les dépendances officielles manquantes et compile
le Studio avec le compilateur .NET Framework de Windows. Le raccourci généré
ouvre le Studio, son serveur et les capteurs intégrés. Aucune dépendance ne
provient d’un dossier LibreHardwareMonitor installé sur le poste de l’auteur.

Pour fabriquer l’installateur, le portable et les sources propres :

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build-release.ps1
```

Les résultats sont écrits dans `dist`. Les détails, tests et prérequis sont dans
[docs/BUILD.md](docs/BUILD.md). Les scripts téléchargent leurs outils dans `.build`.

## Architecture

- `desktop/` : application Windows C# WinForms / WebView2, icône et moteur de capteurs.
- `server.py`, `desktop_backend.py` : serveur FastAPI, WebSockets et cycle de vie.
- `audio_sessions.py`, `monitoring.py`, `discord_rpc.py` : intégrations Windows.
- `admin.html`, `studio*.js`, `studio-shell.css` : Studio de configuration.
- `index.html`, `deck-layout.*` : pupitre mobile et grille partagée.
- `packaging/`, `.github/workflows/` : distributions et automatisation.

L’API d’administration est locale au PC. Le téléphone est associé par un lien
privé. Utiliser uniquement un réseau privé de confiance ; ne pas exposer le
port 5000 sur Internet. Voir [SECURITY.md](SECURITY.md).

## Licence et composants tiers

Le code de DeckEdge est sous [MIT](LICENSE). Les composants tiers gardent leurs
licences et leurs auteurs : [mentions](desktop/THIRD-PARTY-NOTICES.md).
Les distributions incluent les licences, un inventaire des dépendances et les
sources correspondant aux composants matériels redistribués.

DeckEdge est un projet indépendant, sans affiliation à Elgato, Corsair, Discord
ou Microsoft. Les noms de produits appartiennent à leurs propriétaires.

## Retours et limites de la version de test

- Windows x64 uniquement ; les autres systèmes hôtes ne sont pas pris en charge.
- Une seule instance peut utiliser le port TCP 5000 à la fois.
- La disponibilité des capteurs dépend du matériel, des pilotes et des droits Windows.
- Une application audio doit avoir créé une session audio pour apparaître dans la liste.
- L’intégration Discord est facultative et demande ses propres identifiants de configuration.
- Les exécutables DeckEdge ne sont pas encore signés et n’ont pas encore été validés
  sur une machine Windows vierge ou un ensemble représentatif de matériels.

Pour un bug, [ouvrir une issue](https://github.com/Lorzo595/DeckEdge/issues)
en précisant la version, Windows, le mode installé/portable, les étapes et le
comportement attendu. Masquer les chemins personnels, les noms de compte, les
jetons Discord et les liens privés de téléphone avant de joindre une capture
ou un extrait de journal. Ne jamais publier le dossier de données complet.

Les contributions sont les bienvenues : voir [CONTRIBUTING.md](CONTRIBUTING.md).
Pour un problème de sécurité, suivre [SECURITY.md](SECURITY.md).

## Contributeurs

- [Lorzo595](https://github.com/Lorzo595) — création et développement de DeckEdge.
- [xavco63](https://github.com/xavco63) — fiabilisation de la configuration, de l’audio et des états du pupitre ([PR #2](https://github.com/Lorzo595/DeckEdge/pull/2)).

Développé avec l’aide de **ChatGPT**. Merci aux projets libres utilisés par DeckEdge, notamment LibreHardwareMonitor et QRCoder ; leurs licences sont incluses dans les distributions.
