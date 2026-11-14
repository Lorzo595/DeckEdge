# Construire DeckEdge sous Windows

## Environnement

Windows x64, .NET Framework 4.8, PowerShell 5.1 ou 7, accès HTTPS à Python.org,
PyPI, NuGet et GitHub. Le compilateur C# de .NET Framework est utilisé ; Visual
Studio n’est pas nécessaire. Git et Node.js ne sont nécessaires que pour contribuer
ou lancer les tests navigateur. Le logiciel vise Windows 10 build 19041+ / Windows 11.

## Une commande pour les trois distributions

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build-release.ps1
```

Le script télécharge des composants dans `.build`, contrôle les empreintes
de `packaging/dependencies.json`, crée Python 3.14.9 embarqué et ses dépendances
verrouillées, compile le Studio et construit les archives ainsi que l’installateur.
Il installe le compilateur Inno Setup dans `.build/tools/InnoSetup` pour l’utilisateur
courant si nécessaire. Aucun outil de construction n’est installé dans le portable.
Vous pouvez fournir un Inno Setup déjà installé avec `-IsccPath "...\ISCC.exe"`.
`-PortableOnly` évite l’installation d’Inno Setup et ne produit pas de Setup.exe.

Les sorties vont dans `dist`. `.build/latest-release.json` indique le dossier
portable et le dossier de sources nettoyées. Les dossiers de préparation sont
nouveaux à chaque construction pour éviter de réintroduire d’anciennes données.
Les scripts n’effacent jamais la configuration du poste de développement.

Le runtime embarqué est isolé par `python314._pth` ; son chemin vers le serveur
reste relatif. Les bibliothèques sont copiées sans caches Python ni scripts
d’installation contenant des chemins absolus. `--check` teste le serveur avec
des données temporaires. Les tests Python sont exécutés avant l’installateur.

Les composants de capteurs sont téléchargés depuis LibreHardwareMonitor 0.9.6,
jamais depuis une application LHM installée à côté du projet. Les notices et les
sources exactes de LibreHardwareMonitor, PawnIO.Modules et PawnIO sont incluses.
Les licences .NET viennent des paquets NuGet correspondants, et les licences
Python des distributions installées. Le bootstrapper WebView2 est vérifié par
sa signature Authenticode Microsoft ; sa version Evergreen peut évoluer.

Les dépendances directes et transitives sont verrouillées dans requirements.txt.
Les empreintes ne constituent pas une compilation bit pour bit reproductible :
horodatages, signatures des prérequis et outils peuvent varier. Le bootstrap
get-pip est fixé à un commit officiel. Tout échec SHA256 interrompt la construction ;
vérifiez l’origine, mettez à jour le manifeste et testez avant une nouvelle version.

## Vérifications

```powershell
packaging\check-release.ps1
.venv\Scripts\python.exe -m unittest discover -s tests -t . -p "test_*.py"
```

Les tests réseau vérifient l’association par clé, le cookie privé, le refus
d’administration distante et les origines WebSocket. Les tests existants couvrent
l’audio, le profil de démarrage, les tailles de widgets et le monitoring.

Après avoir quitté toute copie de DeckEdge, `packaging/smoke-test.ps1` extrait
le portable dans un chemin contenant des espaces, le lance avec un PATH sans
Python, vérifie le serveur, les capteurs limités, la sauvegarde et l’arrêt.
`-IncludeInstaller` teste aussi l’installation et la désinstallation dans `.build`,
avec des données isolées et sans activer le démarrage automatique. Cette option
refuse de fonctionner si DeckEdge est déjà installé pour l’utilisateur courant.
Ce test local ne remplace pas une validation dans une VM Windows propre.

Les tests navigateur nécessitent Node.js, Playwright et Edge. Pour les installer
sans ajouter de dépendance de production : `npm install --no-save playwright`.
Lancer le serveur sur 127.0.0.1:5000 puis :

```powershell
node tests/studio-shell.cjs
node tests/studio-ergonomics.cjs
node tests/studio-colors.cjs
node tests/mobile-preview.cjs
node tests/mobile-gestures.cjs
node tests/startup-profile.cjs
```

Si le port 5000 est déjà utilisé par une autre copie de DeckEdge, lancer le
serveur de test sur un autre port et pointer les tests dessus :

```powershell
.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 5001
$env:DECKEDGE_TEST_URL = 'http://127.0.0.1:5001'
```

Les tests du Studio interceptent les profils et les sauvegardes ; ils ne doivent
pas modifier les profils réels. Ne jamais activer une commande réelle pour tester
un changement visuel. Pour une validation finale, tester l’installation et la
désinstallation sur une VM Windows propre, puis le portable déplacé dans un
chemin contenant des espaces. Vérifier un PC sans Python et, si possible, sans
WebView2/PawnIO pour les parcours d’installation des prérequis.

## Exécution depuis les sources

Créer un environnement Python avec requirements.txt, puis `desktop/build.ps1`.
Le Studio cherche un Python compatible dans les installations utilisateur et PATH.
Les données restent dans le projet en développement. On peut aussi exécuter
`python server.py` pour le serveur seul ; les capteurs intégrés nécessitent le Studio.

Pour un test isolé : définir `DECKEDGE_DATA_DIR` avant de lancer le serveur Python.
Le build natif de développement conserve les données existantes du projet.

## Changer de version

Mettre à jour VERSION, les deux attributs de version dans desktop/AssemblyInfo.cs,
CHANGELOG.md et docs/RELEASE-NOTES.md. Reconstruire, contrôler les archives et
tester les exécutables avant de créer le tag GitHub correspondant.
