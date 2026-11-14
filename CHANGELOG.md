# Historique

## Non publié

- Pupitre mobile et Studio en français ou anglais, avec bascule mémorisée par appareil.

## 0.1.3 — Profils, sauvegardes et diagnostic

- Restauration annulée si la sauvegarde de sécurité échoue, avec conservation de la configuration actuelle.
- Enregistrement et restauration du Studio protégés contre les opérations concurrentes.

- Export/import JSON des profils et sauvegardes locales horodatées avec restauration depuis le Studio.
- Panneau **Diagnostic** dans le Studio avec rapport local copiable et téléchargeable, chemins, clé et IP privées masqués.
- Port du serveur configurable via `DECKEDGE_PORT` ; si le port 5000 est occupé par un autre logiciel, DeckEdge choisit automatiquement le suivant et le QR code utilise le bon port.
- Sauvegarde de configuration différée et regroupée, avec écriture forcée à l’arrêt et à l’enregistrement manuel.
- Reprise effective des écritures après une erreur temporaire, port serveur mémorisé dans les préférences et garde-fou sur les dossiers de test.
- Le port mémorisé est conservé lors de l’application des paramètres du Studio.
- Masquage du diagnostic insensible à la casse et aux séparateurs Windows/Linux.
- Tests Playwright Studio/mobile et test C# des préférences exécutés dans GitHub Actions ; script local `tests/run-ui-tests.ps1`.

## 0.1.2 — Fiabilité et contributions

- Contribution de xavco63 (PR #2), complétée par des correctifs de verrouillage Discord et de réactivité des commandes.
- Volume relatif des périphériques et cibles audio préfixées corrigés ; reprises bornées des écritures Windows.
- Démarrage Windows par raccourci vérifié, migration de l’ancienne inscription et nettoyage à la désinstallation.
- Maintien en éveil du PC et de l’écran, renouvelé en arrière-plan.
- Liste des contributeurs dans À propos et à la fin du README.

- Sauvegarde de configuration sérialisée : plus d’écriture concurrente sur le même fichier temporaire et plus de perte d’une modification pendant la synchronisation matérielle.
- Récupération fiable d’une configuration corrompue depuis `config.json.bak`.
- Identifiants de boutons/pages normalisés et uniques ; validation des messages WebSocket et limitation des clics.
- Icône et libellé actifs calculés de la même façon dans le Studio, le pupitre et le serveur.
- Cibles audio vides neutralisées, volume relatif des périphériques pris en charge, échappement renforcé dans le Studio.
- Rotation des journaux, clé du téléphone écrite de façon atomique, tests isolés du profil de développement.

## 0.1.1 — Connexion du téléphone simplifiée

- Écran de connexion avec QR code généré localement, accessible depuis le Studio et l’icône près de l’horloge.
- Adresse permanente propre au PC grâce à la découverte mDNS, avec adresse IP de secours.
- Clé d’association conservée au redémarrage et raccourci sur l’écran d’accueil du téléphone.
- Reprise de la découverte quand le réseau revient ; aide de reconnexion plus lisible.
- Crédit développeur Lorzo595 et liens vers le nouveau nom GitHub.
- Contrôles de lecture du QR code, de persistance et de sécurité ; 32 tests Python.

## 0.1.0 — Première distribution publique

- Studio Windows avec profils, bibliothèque d’actions et aperçu mobile.
- Raccourcis clavier, applications, multimédia et volume par application.
- Monitoring LibreHardwareMonitor intégré ; aucun programme LHM séparé nécessaire.
- Distribution Windows x64 avec installateur et archive portable autonome.
- Python embarqué, données isolées, association privée du téléphone et administration locale.
- Sources MIT, mentions tierces et automatisation des versions GitHub.
