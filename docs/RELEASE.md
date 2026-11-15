# Publishing the project on GitHub

## First publication

1. Build with `packaging/build-release.ps1`, then run `packaging/check-release.ps1`.
2. Open `.build/latest-release.json`: the `source` field points to a **DeckEdge**
   folder containing only the public files. Publish that folder, or extract
   `dist/DeckEdge-0.1.5-Source.zip` and publish its contents.
3. Create a public GitHub repository, then push these sources to it. Include the
   hidden `.gitignore` and `.github` files. Do not push the full working folder
   containing your profiles, WebView2 cache, logs or credentials.
4. Enable Actions. Pushes and pull requests build the Windows packages.
5. Update the README with a link to your own repository's Releases.

Example from the cleaned source folder:

```powershell
git init
git add .
git commit -m "Initial public release"
git branch -M main
git remote add origin https://github.com/YOUR-ACCOUNT/DeckEdge.git
git push -u origin main
git tag v0.1.5
git push origin v0.1.5
```

The `v0.1.5` tag must match VERSION. The workflow creates a **draft Release**
with the installer, the portable build, the sources and SHA256SUMS.txt. Check the
files and the notes, then click **Publish release** to make them downloadable.
Users download the files from **Releases**, not the automatic "Code → Download ZIP"
archive, which contains only the sources.

Without Actions: create a Release manually, attach the four files from `dist`,
use docs/RELEASE-NOTES.md as the notes, then publish.

Release titles and release notes must be written in English.

## Before each publication

- Install, launch, quit and uninstall on a clean Windows VM.
- Test the portable build after moving its folder, with a path containing spaces.
- Check phone pairing and that data survives an update.
- Never rebuild by simply zipping your personal working folder.
- Review the licenses, inventories and hashes of the new components.

The packages are not signed with a DeckEdge publisher certificate. An Authenticode
signature with your own certificate can be added before publication.
Never store that certificate or its secrets in the sources; use GitHub Actions
secrets for a future signing step.

The workflow only requests read permissions to build, and `contents: write` in
the job that creates the draft Release. Pull requests do not publish a Release
and do not receive publishing secrets.
