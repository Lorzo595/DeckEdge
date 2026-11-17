# DeckEdge 0.1.6 — Visual library, redesigned Studio and phone management

## What's new

- A cleaner desktop Studio with profile navigation on the left, a faithful phone preview in the centre, a compact action library on the right and key settings below the preview.
- A visual library for PNG, JPEG, WebP, ICO, safe static SVG and animated GIF files. Import individual files or ZIP collections, search and filter artwork, and choose separate normal and active/muted visuals.
- Installable starter packs for PC applications and gaming platforms, plus an offline animated-controls pack. Downloaded artwork stays on the PC and is served to the paired phone.
- Export and share ZIP packs. Profile exports embed their referenced artwork, including active-state images, so they can move to another PC.
- A Phones panel to list paired devices, rename them and revoke one or all. Each phone receives its own token; revocation closes active sessions and refreshes the pairing link.

## Fixes and reliability

- Prevent invisible keys being added to navigation folders. Keep sub-pages next to their folder in the Studio.
- Keep the inspector reachable at 100% preview zoom and prevent overflow on small windows.
- Refresh open QR dialogs after pairing-key rotation while preserving the selected network address.
- Migrate older phone cookies and WebSockets to individual device sessions; check authorisation during connection setup and before commands.
- Preserve artwork and the private phone registry during updates. Exclude personal media, pairing secrets and phone registries from public archives.
- Enforce LF line endings in the repository and run updater handoff, bilingual dialogs and packaging privacy checks in CI.

## Update or install

- **From 0.1.5:** open Settings or the tray menu, then Check for updates. Enable pre-release updates to see this public test release. Profiles, phone pairing and user media are preserved.
- **Older versions:** use the setup executable, or replace your portable application files while keeping your `data` folder.
- Source/development checkouts are not overwritten by the packaged updater.

### Downloads

- `DeckEdge-0.1.6-Setup-x64.exe`: standard Windows installation.
- `DeckEdge-0.1.6-Portable-x64.zip`: extract the entire archive and run `DeckEdge/DeckEdge.exe`.
- `DeckEdge-0.1.6-Source.zip`: clean public source code under MIT.
- `SHA256SUMS.txt`: package checksums.

Windows 10 (2004+) / Windows 11, x64. The PC and phone must share a private network. The executables are unsigned; this remains a public test release pending validation on more PCs.

Thanks to **xavco63** for phone management, updater CI and line-ending cleanup. Developed by **Lorzo595**.
