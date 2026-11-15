# In-app updates

The updater first ships in 0.1.5. An older version needs one initial manual
installation or portable-folder migration; it cannot acquire a feature that it
does not yet contain. The source/development layout is deliberately not replaced
with a packaged release. Use an installed or portable edition for in-app updates.

## Using it

Open **Settings → Check for updates**, or right-click the tray icon and choose
**Check for updates**. Opening the window checks the official GitHub releases.
For 0.x builds, pre-releases are included by default; uncheck the option to look
only for stable releases. No scheduled checks or background downloads occur.

Review the notes and select **Update and restart**. Save the Studio first.
You can cancel the download or close the window before installation; application
files remain unchanged. The app asks before downloading and restarting.

## What is preserved

- The current folder and installed/portable mode. The portable marker is never
  introduced into an installed edition or overwritten in portable mode.
- Profiles, settings, backups, Discord configuration, the phone pairing key and
  the paired-device registry.
- A custom `DECKEDGE_DATA_DIR`, including when restarting the app.
- Startup shortcuts: the executable path stays the same. The installed edition's
  uninstall display version is refreshed only if its registered path matches.
- Files that are not present in the update package are left alone.

## Validation and replacement

Only numeric `vX.Y.Z` releases with a Windows x64 portable asset and SHA256SUMS.txt
are considered. Drafts and incomplete releases are skipped. The portable package
is used for both editions, so no reinstall wizard or new privilege is required.

Downloads use HTTPS with certificate validation and a fixed GitHub destination
allowlist. The package's size, SHA256, version and archive paths are checked before
shutdown; traversal paths, duplicate files and private-data paths are rejected.
Checksums provide download integrity; they are not a substitute for a signed
publisher identity. DeckEdge binaries are still unsigned.

A separate helper waits for the old process to exit, including server and sensor
cleanup. It acquires the installation's instance mutex, rechecks the downloaded
archive and refuses same-version/downgrade operations. It backs up every existing
file that it will replace before the first write. On a replacement error, written
files are restored and newly introduced files removed. Profile directories are
outside this transaction. The updated app then restarts with the same data folder.

## Recovery and limitations

On preparation failure, the running app is unchanged. On replacement failure,
the helper reports whether restoration succeeded. It keeps its backup and error
report under the specific `%TEMP%\DeckEdge-update-<id>` directory; if restoration
is incomplete, the error dialog gives the backup path. Do not delete that backup
before recovering the files. Successfully completed updates remove the large
archive/extraction/backup copies; the small helper and plan may remain in Temp.

Protected or linked installation folders may prevent an update; move the portable
edition to a writable folder or use the normal installer. The updater does not
force-kill another running copy. A power loss or forced termination during file
replacement still requires manual recovery from the backup or installer. Startup
of the new app is requested, but a full health check after restart is not performed.

## Tests

`tests/run-update-smoke.ps1` checks release/channel selection, official asset URLs,
hashes, archive traversal/duplicates, rollback, cancellation and data preservation.
`tests/run-update-e2e.ps1` runs the actual helper against two disposable stub apps
to verify installed/portable replacement and restart with the original data folder.
`tests/run-update-ui-smoke.ps1` renders both language versions and checks that the
action buttons fit in the window. Fixtures stay under `.build`; the developer's
profiles and Windows startup registration are not modified.
The GitHub test job runs all three scripts before the browser tests.
