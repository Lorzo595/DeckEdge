# DeckEdge

Turn your phone into a control deck for Windows: shortcuts, apps, music,
per-app volume and hardware monitoring. The Windows Studio lets you organize
everything with a mobile preview, an action library and simple settings.
No physical Stream Deck required.

**Windows 10 (2004+) / Windows 11 · x64 · version 0.1.5 · MIT license**

Built by **Lorzo595**.

> **Public test version.** DeckEdge 0.1.5 works and has been tested
> on the development machine, but validation across multiple PCs and user
> feedback are still needed before a 1.0.0 release.

[Download version 0.1.5](https://github.com/Lorzo595/DeckEdge/releases/tag/v0.1.5)
· [Report an issue](https://github.com/Lorzo595/DeckEdge/issues)
· [Quick start guide](docs/QUICKSTART.md)

## Features

| Area | What DeckEdge lets you do |
| --- | --- |
| Windows Studio | Dedicated window, tray icon near the clock, local settings and optional launch at startup |
| Mobile deck | Interface in the phone browser, portrait or landscape, on the same private network as the PC |
| PC connection | First pairing by local QR code, key kept and a permanent address specific to the PC for later visits |
| Profiles | Multiple pages, folders and sub-pages, add, rename, duplicate and move keys |
| Organization | Phone preview, drag and drop, and widgets with adjustable width and height |
| Actions | Keyboard shortcuts, media keys, launching apps, files and websites, plus multi-step sequences with conditions |
| Testing | Validate a key, application or audio target from the Studio without running the action |
| Audio | Windows volume, audio outputs and apps with an active audio session, with sliders and mute |
| Monitoring | Built-in LibreHardwareMonitor engine and a choice of 1 to 6 sensors, with an optional secondary reading |
| Customization | Name, searchable icon library, colors, eyedropper and active/inactive states for toggle keys |
| Accessibility | Phone pinch zoom, `aria-pressed` toggle states and reduced-motion support |
| Languages | Deck, Studio and Windows app interface in French or English, with the choice remembered |
| Editing | Library with search, right-click, duplication, undo/redo and keyboard shortcuts |
| Profiles | JSON export/import and local backups with restore |
| Diagnostics | Copyable local report with paths, key and private IPs masked |
| Discord | Optional RPC integration for the mic and mute, requiring your own Discord setup |

The phone needs no app installed and no DeckEdge account. Commands run on the PC;
the phone acts as a remote. The software requires no subscription and its code
is available under MIT.

## Download

In the [0.1.5 Release](https://github.com/Lorzo595/DeckEdge/releases/tag/v0.1.5), choose:

| File | Purpose |
| --- | --- |
| `DeckEdge-0.1.5-Setup-x64.exe` | Standard installation, shortcuts and Windows uninstall |
| `DeckEdge-0.1.5-Portable-x64.zip` | Unzip, then run `DeckEdge/DeckEdge.exe`; everything stays in that folder |
| `DeckEdge-0.1.5-Source.zip` | Clean sources to publish, study or modify |
| `SHA256SUMS.txt` | Checksums for the files in this version |

Python and the LibreHardwareMonitor engine are included. You do not need
to install Python, Chrome or the LibreHardwareMonitor application.
Microsoft WebView2 Runtime is required; DeckEdge offers to install it
if missing (Internet connection required). The PawnIO driver is offered for
some temperatures and hardware readings; it requires administrator consent.
The Studio runs without administrator rights, with limited readings if
full hardware access is refused.

### Standard installation

1. Download `DeckEdge-0.1.5-Setup-x64.exe` from the Release.
2. Follow the wizard. Installation is for the current user, with
   a Start menu shortcut and an optional Desktop shortcut.
3. Open DeckEdge. Accept the WebView2 installation if it is missing and choose
   whether full hardware access is wanted.
4. Uninstall through the Windows installed apps list; profiles
   are kept in the user data folder.

### Portable version

1. Download `DeckEdge-0.1.5-Portable-x64.zip` and extract the **entire** archive.
2. Open the `DeckEdge` folder, then run `DeckEdge.exe`.
3. Keep `runtime`, the libraries and `portable.flag` together. Data
   is created in `data`; move the whole folder to take the deck with you.

WebView2 and the PawnIO hardware driver remain system components: portable
mode covers DeckEdge and its data, not the installation of these prerequisites.
It can work offline once the prerequisites are present, except for actions
that open online services. Do not download the GitHub "Code" ZIP
to install the app: that ZIP contains the sources and no ready-to-run executable.

The executables of this first version are not signed with a DeckEdge
publisher certificate. Windows may show a SmartScreen warning. Distribute
only files you built or downloaded from the original Release, and verify their
checksum if in doubt.

## Getting started

### In-app updates

Open **Settings → Check for updates**, or use the same command from the tray icon.
Review the release notes, then select **Update and restart**. DeckEdge downloads
and verifies the official package before closing; profiles, settings and phone
pairing are kept in place. Installed and portable editions stay in their current
folder and mode. Save any Studio changes first. Preparation can be cancelled.

Older builds need one manual installation of a build containing the updater;
after that, future updates can be applied inside DeckEdge. There are no automatic
background downloads. See [Update behavior and recovery](docs/UPDATES.md).

1. Install DeckEdge or extract the **entire** folder from the portable archive to
   a location you can write to. Run `DeckEdge.exe`.
2. In the Studio, choose a profile, add an action from the library,
   then select the key to set its name, icon and color.
3. Click **Save**. Right-click, drag and drop, Ctrl+Z and Ctrl+S
   make work faster.
4. Connect the phone to the same private network as the PC. In DeckEdge,
   **Connect phone** displays a private QR code to scan. Choose
   **This PC · permanent address**, then add the page opened on the phone's
   home screen or to bookmarks: a new scan is not needed
   at each startup. The link can always be copied as a fallback.
5. If Windows Firewall asks, allow DeckEdge/Python on the
   **private** network only. The server uses TCP port 5000, or the next one if it
   is already in use; the QR code always shows the right port.

Closing the window keeps DeckEdge near the clock by default. The menu of
that icon lets you reopen the Studio, quit completely, view the logs
or open the data folder. **Settings** in particular handles launch at startup.
The **About DeckEdge** section shows the version, developer,
license and credits for the main components, with access to the license text.
Only one copy of DeckEdge should use a given port at a time. If port
5000 is taken by other software, DeckEdge automatically chooses the next
port and remembers it for later launches. If another copy of
DeckEdge is already running, quit it before opening the installed or portable version.

[Quick start guide](docs/QUICKSTART.md) · [Building](docs/BUILD.md) ·
[GitHub publishing](docs/RELEASE.md) · [Internationalization](docs/I18N.md) ·
[Security](SECURITY.md)

The permanent address uses local mDNS discovery (`.local`) and stays specific
to the PC even if its IP address changes. The pairing key stays in DeckEdge's
data: neither a restart nor a GitHub username change alters it.
On a network that blocks multicast, choose the fallback Wi-Fi/Ethernet address
in the QR screen; that IP address can change. Erasing DeckEdge's data
or removing the shortcut and the browser pairing may require a new scan.

## Your data

- Installed version: `%LOCALAPPDATA%\DeckEdge`.
- Portable version: `data` next to `DeckEdge.exe`.
- Development from sources: the project folder, unless
  `DECKEDGE_DATA_DIR` points to another location.

Profiles, settings, the phone key and Discord credentials are never
included in distributions produced by the build scripts.
Uninstalling keeps profiles. To migrate, quit both versions
then copy your data files into the new folder; reconnect the
Discord account if needed. Back up the folder before an update.

To update a portable version: extract the new version into a
new folder, then copy the old `data` folder into it. Do not mix
libraries from different versions. Keep `portable.flag` next to the executable.
Automatic startup of a portable copy must be re-enabled if you move it.

## Development

Windows x64, Python 3.14 and .NET Framework 4.8 are recommended.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m unittest discover -s tests -t . -p "test_*.py"
powershell -ExecutionPolicy Bypass -File tests\run-csharp-smoke.ps1
npm install --no-save playwright
powershell -ExecutionPolicy Bypass -File tests\run-ui-tests.ps1
powershell -ExecutionPolicy Bypass -File desktop\build.ps1
```

`desktop/build.ps1` fetches missing official dependencies and compiles
the Studio with the Windows .NET Framework compiler. The generated shortcut
opens the Studio, its server and the built-in sensors. No dependency
comes from a LibreHardwareMonitor folder installed on the author's machine.

For tests or an isolated run, `DECKEDGE_DATA_DIR` moves the data and
`DECKEDGE_PORT` forces the server's TCP port. Without this variable, port 5000
is used, then the next one if it is busy.

To build the installer, the portable version and the clean sources:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build-release.ps1
```

Results are written to `dist`. Details, tests and prerequisites are in
[docs/BUILD.md](docs/BUILD.md). The scripts download their tools into `.build`.

## Architecture

- `desktop/`: C# WinForms / WebView2 Windows app, icon and sensor engine.
- `server.py`, `desktop_backend.py`: FastAPI server, WebSockets and lifecycle.
- `audio_sessions.py`, `monitoring.py`, `discord_rpc.py`: Windows integrations.
- `admin.html`, `studio*.js`, `studio-shell.css`: configuration Studio.
- `index.html`, `deck-layout.*`: mobile deck and shared grid.
- `packaging/`, `.github/workflows/`: distributions and automation.

The admin API is local to the PC. The phone is paired through a private
link. Use only a trusted private network; do not expose the server
port to the Internet. See [SECURITY.md](SECURITY.md).

## License and third-party components

DeckEdge code is under [MIT](LICENSE). Third-party components keep their
licenses and authors: [notices](desktop/THIRD-PARTY-NOTICES.md).
Distributions include the licenses, a dependency inventory and the
sources for the redistributed hardware components.

DeckEdge is an independent project, not affiliated with Elgato, Corsair, Discord
or Microsoft. Product names belong to their owners.

## Feedback and public test limitations

- Windows x64 only; other host systems are not supported.
- TCP port 5000 is used by default. If another program occupies it,
  DeckEdge automatically chooses the next port; only one DeckEdge
  instance should use a given port.
- Sensor availability depends on hardware, drivers and Windows permissions.
- An audio app must have created an audio session to appear in the list.
- Discord integration is optional and requires its own configuration credentials.
- DeckEdge executables are not yet signed and have not yet been validated
  on a clean Windows machine or a representative set of hardware.

For a bug, [open an issue](https://github.com/Lorzo595/DeckEdge/issues)
stating the version, Windows, installed/portable mode, steps and expected
behavior. Mask personal paths, account names, Discord tokens and private phone
links before attaching a screenshot or log excerpt. Never publish the full data folder.

Contributions are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md).
For a security issue, follow [SECURITY.md](SECURITY.md).

## Contributors

- [Lorzo595](https://github.com/Lorzo595) — creation and development of DeckEdge.
- [xavco63](https://github.com/xavco63) — French/English interfaces, action validation, conditional sequences, folders, configuration and audio reliability, diagnostics and backups ([PR #2](https://github.com/Lorzo595/DeckEdge/pull/2), [#4](https://github.com/Lorzo595/DeckEdge/pull/4), [#5](https://github.com/Lorzo595/DeckEdge/pull/5), [#9](https://github.com/Lorzo595/DeckEdge/pull/9), [#10](https://github.com/Lorzo595/DeckEdge/pull/10), [#11](https://github.com/Lorzo595/DeckEdge/pull/11), [#12](https://github.com/Lorzo595/DeckEdge/pull/12)).

Thanks to the open-source projects used by DeckEdge, in particular LibreHardwareMonitor and QRCoder; their licenses are included in the distributions.
