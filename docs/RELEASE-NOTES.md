# DeckEdge 0.1.4 — Folders, conditional actions and bilingual interfaces

Windows x64 pre-release by **Lorzo595**. Thanks to **xavco63** for the French/English interfaces, action tools and folder navigation.

## What's new since 0.1.3

- **Folders and sub-pages:** organize pages into one-level folders in the Studio and on your phone. Rename, duplicate or delete a folder; deleting a folder keeps its pages at the top level. The phone remembers the last visited sub-page of each folder for the current session.
- **Action validation:** use **Test** in the Studio to check shortcuts, application targets, audio targets and sequence conditions without executing commands. Validation uses your current unsaved configuration.
- **Conditional sequences:** run a step only when a toggle is on/off, an application is running, or the microphone is muted/live. Unmet conditions skip the step; an action failure stops the sequence.
- **Icon library:** search categorized icons and reuse recently selected icons.
- **French and English:** the Studio, mobile deck, pairing screen and native Windows interface remember your language choice. Repository documentation is now in English.
- **Mobile accessibility:** pinch zoom is enabled and toggle/mute controls expose their pressed state to assistive technology.

## Fixes included after review

- Copied profiles and folders keep their own internal condition links, including references between sub-pages. References to keys outside the copied group remain unchanged.
- Sequence button conditions read the latest state before each step instead of using a snapshot from sequence startup. Missing or non-toggle condition keys do not satisfy the condition.
- Audio validation recognizes relative volume and mute commands for output devices and the `general` output alias.

QR pairing, the permanent PC address, local backups, diagnostics, Windows startup and the keep-awake option remain available.

## Downloads and installation

| File | Use |
| --- | --- |
| `DeckEdge-0.1.4-Setup-x64.exe` | Standard Windows installation; follow the setup wizard. |
| `DeckEdge-0.1.4-Portable-x64.zip` | Extract the entire archive and run `DeckEdge/DeckEdge.exe`. |
| `DeckEdge-0.1.4-Source.zip` | Clean public sources under the MIT license. |
| `SHA256SUMS.txt` | SHA-256 checksums for the three downloads. |

Requires **Windows 10 build 19041+ or Windows 11, x64**. Python and LibreHardwareMonitor are bundled. WebView2 is offered if missing and requires Internet for installation. Full hardware sensor access is optional and may request administrator permission.

## Updating from an earlier version

1. Quit the previous version completely using its tray icon near the Windows clock.
2. Run the new installer, or extract the new portable archive into a new folder.
3. For portable mode, copy your old `data` folder into the new DeckEdge folder to preserve profiles, backups and the phone pairing key. The installed edition keeps its data in `%LOCALAPPDATA%\DeckEdge`.
4. Reopen DeckEdge. Your existing flat pages remain supported; folders are optional.

Your phone pairing key is preserved. If a port conflict forces a different server port, open **Connect phone** and scan the updated QR code; the selected port is remembered afterwards.

## Validation and limitations

- 90 Python tests, 14 Edge browser test scripts, and the C# preferences smoke test.
- Regression coverage for live sequence conditions, internal/external copied links, cross-page folder links, and device audio validation without executing commands.
- Windows installer/portable builds and clean-distribution/SHA-256 checks.

This is still a **pre-release**, not 1.0.0. Executables are unsigned, so Windows SmartScreen may show a warning. Clean Windows installation, a representative range of hardware and full Windows restart scenarios still need broader manual validation. Automated action tests use mocks.

Keep the PC and phone on the same private network. Do not expose the HTTP server to the Internet or share your QR code/pairing key. Review profile exports and diagnostics before sharing them: they may contain personal information.

[Documentation](https://github.com/Lorzo595/DeckEdge#readme) · [Contributors](https://github.com/Lorzo595/DeckEdge#contributors) · [Report an issue](https://github.com/Lorzo595/DeckEdge/issues)
