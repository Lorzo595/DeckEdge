# Publier le projet sur GitHub

## Première publication

1. Construire avec `packaging/build-release.ps1`, puis lancer `packaging/check-release.ps1`.
2. Ouvrir `.build/latest-release.json` : le champ `source` désigne un dossier
   **DeckEdge** contenant uniquement les fichiers publics. Publier ce dossier,
   ou extraire `dist/DeckEdge-0.1.1-Source.zip` puis publier son contenu.
3. Créer un dépôt GitHub public, puis y envoyer ces sources. Inclure les fichiers
   cachés `.gitignore` et `.github`. Ne pas envoyer le dossier de travail complet
   contenant vos profils, votre cache WebView2, vos logs ou vos identifiants.
4. Activer Actions. Les pushs et pull requests construisent les paquets Windows.
5. Mettre à jour le README avec un lien vers les Releases de votre propre dépôt.

Exemple depuis le dossier de sources nettoyées :

```powershell
git init
git add .
git commit -m "Initial public release"
git branch -M main
git remote add origin https://github.com/VOTRE-COMPTE/DeckEdge.git
git push -u origin main
git tag v0.1.1
git push origin v0.1.1
```

Le tag `v0.1.1` doit correspondre à VERSION. Le workflow crée une **Release brouillon**
avec l’installateur, le portable, les sources et SHA256SUMS.txt. Vérifier les fichiers
et les notes, puis cliquer sur **Publish release** pour les rendre téléchargeables.
Les utilisateurs téléchargent les fichiers dans **Releases**, et non le ZIP automatique
« Code → Download ZIP », qui contient uniquement les sources.

Sans Actions : créer manuellement une Release, y joindre les quatre fichiers de
`dist`, utiliser docs/RELEASE-NOTES.md comme notes, puis publier.

## Avant chaque publication

- Installer, lancer, quitter et désinstaller dans une VM Windows propre.
- Tester le portable après déplacement de son dossier, avec un chemin contenant des espaces.
- Vérifier la connexion d’un téléphone et le maintien des données après mise à jour.
- Ne jamais reconstruire par simple ZIP du dossier de travail personnel.
- Examiner les licences, les inventaires et les empreintes des nouveaux composants.

Les paquets ne sont pas signés avec un certificat éditeur DeckEdge. Une signature
Authenticode avec votre propre certificat pourra être ajoutée avant publication.
Ne stockez jamais ce certificat ou ses secrets dans les sources ; utilisez les
secrets GitHub Actions pour une future étape de signature.

Le workflow demande seulement les permissions de lecture pour construire et
`contents: write` dans le job qui crée la Release brouillon. Les pull requests
ne publient pas de Release et ne reçoivent pas de secrets de publication.
