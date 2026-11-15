# DeckEdge 0.1.3 — Profiles, backups and diagnostics

Windows x64 pre-release developed by **Lorzo595**, with the help of **ChatGPT**. Thanks to **xavco63** for the contributions merged in PR #4 and #5.

## What's new since 0.1.2

- **Profiles** menu: JSON export, validated import that can be cancelled before saving.
- Local **timestamped backups**: the last 20 are kept and can be restored from the Studio.
- Safety backup before a restore; if it fails, the restore is cancelled and the current configuration is kept.
- Protection against a simultaneous save and restore.
- **Diagnostics** panel with a report you can copy or download, hiding personal paths and known keys and tokens.
- Configurable port with automatic selection on conflict, remembered between launches and kept when applying settings. The QR code and mDNS use the chosen port.
- Configuration writes are grouped together with retry after a temporary error.
- Browser and C# tests included in the GitHub checks; source line ending normalization.

The QR code, the PC's permanent address, Windows startup and keeping the PC and its screen awake are unchanged.

## Download

- **DeckEdge-0.1.3-Setup-x64.exe**: standard Windows installation.
- **DeckEdge-0.1.3-Portable-x64.zip**: extract the whole folder, then run DeckEdge.exe.
- **DeckEdge-0.1.3-Source.zip**: cleaned public sources.
- **SHA256SUMS.txt**: checksums of the downloads.

Windows 10 build 19041+ / Windows 11 **x64**. Python and LibreHardwareMonitor are included. WebView2 is offered if missing; Internet access is then required. Full sensor access remains optional and may require administrator approval.

## Updating

1. Fully quit the old version from its icon near the clock.
2. Install 0.1.3, or extract the new portable build into a new folder.
3. For the portable build, copy the old `data` folder into the new one to keep profiles, backups and the phone key. The standard installation keeps its data in `%LOCALAPPDATA%\DeckEdge`.
4. If a conflict forces a port change and the mobile shortcut no longer responds, reopen **Connect phone** and scan the new QR code. The chosen port is then remembered.

Profile exports may contain your paths and action targets: read them again before sharing. Also review the diagnostics report before publishing it. Never share the QR code or its private key. The PC and phone must stay on the same private network.

## Validation and limitations

68 Python tests, eight Edge tests and the C# test passed on the merged features. The GitHub checks also compile the Windows packages and verify the distributions. Backup failure and concurrent operation cases are covered by regression tests.

This version remains a **pre-release**, not 1.0.0. The executables are unsigned (SmartScreen warning possible). Validation on multiple hardware configurations, on a clean Windows install and after a full Windows restart is still to be completed. Automated command tests use simulations. Do not expose the HTTP server to the Internet.

[Documentation](https://github.com/Lorzo595/DeckEdge#readme) · [Contributors](https://github.com/Lorzo595/DeckEdge#contributors) · [Report an issue](https://github.com/Lorzo595/DeckEdge/issues)
