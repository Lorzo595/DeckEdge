# DeckEdge 0.1.5 — In-app updates

Windows x64 pre-release by **Lorzo595**. This build adds a simple way to apply future DeckEdge updates from inside the application.

## What's new

- Open **Settings → Check for updates**, or use the tray menu. Review the release notes, then choose **Update and restart**.
- Optional pre-release inclusion; enabled by default for 0.x builds. Checks and downloads are manual.
- Official GitHub downloads with file size, SHA256, package version and archive-path validation before shutdown.
- A separate helper waits for DeckEdge to close, updates the files and restarts the app in its existing folder.
- Profiles, settings, phone pairing, custom data directories and installed/portable mode are preserved.
- Replaced files are backed up before writing and restored if replacement fails. Preparation can be cancelled without changing the running app.
- French and English update windows, with a guard against updating unsaved Studio changes or installing an older version.

## First installation of this feature

Versions before 0.1.5 do not contain an updater. Install this version once using the setup file, or migrate your portable `data` folder into this version. Future releases can then be applied inside DeckEdge. Development/source checkouts are not overwritten by packaged updates.

## Downloads

- `DeckEdge-0.1.5-Setup-x64.exe`: standard Windows installation.
- `DeckEdge-0.1.5-Portable-x64.zip`: extract the entire archive, then open `DeckEdge/DeckEdge.exe`.
- `DeckEdge-0.1.5-Source.zip`: clean public sources under MIT.
- `SHA256SUMS.txt`: SHA-256 checksums for the three files.

Requires Windows 10 build 19041+ or Windows 11 x64. Python and LibreHardwareMonitor are included. WebView2 may require its initial installation; full sensor access remains optional.

Quit your old copy before installing or switching portable folders. The installed edition keeps data in `%LOCALAPPDATA%\DeckEdge`; portable mode keeps it in `data` beside the executable. Preserve that folder to keep your phone pairing key. A development checkout stores data in its project folder unless `DECKEDGE_DATA_DIR` is set.

## Validation and limitations

Updater checks cover version selection, official URLs, checksums, unsafe/duplicate archive paths, cancellation, rollback and installed/portable data preservation. The actual helper is tested with isolated applications for process waiting and restart using the same data directory. French/English dialogs and the C# preferences tests are checked. An official GitHub package was downloaded and its checksum verified without executing it.

This remains a pre-release. Binaries are unsigned and SmartScreen may show a warning. Broader clean-Windows and hardware testing is still needed. Protected/linked folders or a forced shutdown during replacement can require manual recovery. The helper requests a restart but does not perform a full post-restart health check. See [update behavior and recovery](https://github.com/Lorzo595/DeckEdge/blob/main/docs/UPDATES.md).

Keep DeckEdge on a trusted private network. Never share the phone QR/pairing key; review diagnostics and profile exports before publishing them.
