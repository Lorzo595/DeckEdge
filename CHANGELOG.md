# Changelog

## Unreleased

- Mobile deck and Studio in French or English, with the choice remembered per device.
- Pairing page and server error messages in French or English.
- Windows interface (icon, settings, dialogs and notifications) in French or English, with the choice remembered on the PC.
- Repository documentation, issue templates and code comments in English.

## 0.1.3 — Profiles, backups and diagnostics

- Restore cancelled if the safety backup fails, keeping the current configuration.
- Studio save and restore protected against concurrent operations.

- JSON export/import of profiles and timestamped local backups, restorable from the Studio.
- **Diagnostics** panel in the Studio with a local report that can be copied or downloaded, with paths, key and private IPs masked.
- Server port configurable via `DECKEDGE_PORT`; if port 5000 is taken by another program, DeckEdge automatically picks the next one and the QR code uses the correct port.
- Deferred, batched configuration saving, with a forced flush on shutdown and on manual save.
- Writes effectively resume after a temporary error, server port remembered in preferences, and a safeguard on test folders.
- The remembered port is kept when Studio settings are applied.
- Diagnostics masking is case-insensitive and handles both Windows and Linux separators.
- Playwright Studio/mobile tests and a C# preferences test run in GitHub Actions; local script `tests/run-ui-tests.ps1`.

## 0.1.2 — Reliability and contributions

- Contribution from xavco63 (PR #2), completed with fixes for Discord locking and command responsiveness.
- Fixed relative volume of devices and prefixed audio targets; bounded retries for Windows writes.
- Verified Windows startup via shortcut, migration of the old registration and cleanup on uninstall.
- PC and screen kept awake, renewed in the background.
- Contributor list in About and at the end of the README.

- Serialized configuration saving: no more concurrent writes to the same temporary file and no more lost change during the hardware flush.
- Reliable recovery of a corrupted configuration from `config.json.bak`.
- Normalized, unique button/page identifiers; WebSocket message validation and click rate limiting.
- Active icon and label computed the same way in the Studio, the deck and the server.
- Empty audio targets neutralized, relative device volume supported, hardened escaping in the Studio.
- Log rotation, phone key written atomically, tests isolated from the development profile.

## 0.1.1 — Simpler phone connection

- Login screen with a locally generated QR code, reachable from the Studio and from the icon near the clock.
- Permanent address specific to the PC thanks to mDNS discovery, with an IP address fallback.
- Pairing key kept across restarts and shortcut on the phone home screen.
- Discovery resumes when the network comes back; clearer reconnection help.
- Developer credit Lorzo595 and links to the new GitHub name.
- Checks for QR code scanning, persistence and security; 32 Python tests.

## 0.1.0 — First public release

- Windows Studio with profiles, action library and mobile preview.
- Keyboard shortcuts, applications, media and per-application volume.
- Integrated LibreHardwareMonitor monitoring; no separate LHM program needed.
- Windows x64 distribution with installer and self-contained portable archive.
- Embedded Python, isolated data, private phone pairing and local administration.
- MIT sources, third-party notices and GitHub release automation.
