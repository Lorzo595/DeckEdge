# DeckEdge 0.1.2 — Fiabilité, démarrage Windows et contributeurs

Préversion de test Windows x64, développée par **Lorzo595**, avec l’aide de **ChatGPT**. Merci à **xavco63** pour sa contribution dans la PR #2.

## Nouveautés

- Sauvegardes sérialisées et récupération des profils depuis leur sauvegarde valide.
- Validation des identifiants et messages du téléphone, affichage des états harmonisé, journaux limités en taille.
- Corrections du verrouillage Discord, des commandes avant sauvegarde et du volume relatif des périphériques.
- Reprises courtes des écritures lorsque Windows bloque temporairement un fichier.
- Démarrage Windows via un raccourci vérifié et détection d’une désactivation système.
- Option pour maintenir le PC et son écran éveillés pendant que DeckEdge reste ouvert.
- Contributeurs dans À propos et dans le README. Le QR code et l’adresse permanente du PC sont conservés.

## Télécharger et mettre à jour

- **DeckEdge-0.1.2-Setup-x64.exe** : installation classique.
- **DeckEdge-0.1.2-Portable-x64.zip** : extraire le dossier et lancer DeckEdge.exe.
- **DeckEdge-0.1.2-Source.zip** : sources publiques ; **SHA256SUMS.txt** : empreintes.

Quitter l’ancienne version depuis son icône près de l’horloge avant la mise à jour. En portable, copier l’ancien dossier `data` dans le nouveau dossier pour conserver profils et association du téléphone. L’installation classique conserve ses données dans `%LOCALAPPDATA%\DeckEdge`.

Le démarrage discret place DeckEdge près de l’horloge. L’option anti-veille concerne l’inactivité ; elle ne remplace pas une veille demandée manuellement. Pour le téléphone, PC et mobile doivent rester sur le même réseau privé ; scanner le QR puis conserver le raccourci. Ne pas partager la clé du QR.

## Validation et limites

53 tests Python et six tests Edge automatisés réussis ; compilation native et demandes Windows de maintien en éveil vérifiées. Les tests de commandes utilisent des simulations : la validation réelle Discord/audio sur plusieurs machines reste à compléter, ainsi que le lancement après une nouvelle ouverture de session Windows et l’installation sur Windows vierge.

Cette version reste une **préversion**, pas la 1.0.0. Exécutables non signés : SmartScreen peut afficher un avertissement. Ne pas exposer le serveur HTTP local sur Internet.

[Documentation](https://github.com/Lorzo595/DeckEdge#readme) · [Contribuer](https://github.com/Lorzo595/DeckEdge/blob/main/CONTRIBUTING.md) · [Signaler un problème](https://github.com/Lorzo595/DeckEdge/issues)
