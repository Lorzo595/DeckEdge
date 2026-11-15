# Getting started with DeckEdge

Developed by Lorzo595. Source code under the MIT license.

## Updating from DeckEdge

Starting with 0.1.5, open **Settings → Check for updates** or use the tray menu.
Save your Studio changes, review the notes and choose **Update and restart**.
The app keeps profiles and phone pairing, verifies the download, closes cleanly
and updates in place. Preparation can be cancelled. Older versions need one
initial manual installation of a build containing this feature; portable users
must copy their old `data` folder on that initial migration. See [UPDATES.md](UPDATES.md).

## Installation
Run Setup-x64.exe, choose the folder and finish the wizard. A shortcut
is added to the Start menu; the desktop shortcut is optional. Uninstalling
goes through Windows installed apps. Profiles are kept.

## Portable
Extract the whole archive into a personal folder, then run DeckEdge.exe.
Keep the executable, the libraries, runtime and portable.flag together.
Profiles are created in data. Move the entire folder to take the Deck with you.
WebView2 is a shared Windows component: if it is missing, DeckEdge offers to install it.
The PawnIO hardware driver is also an optional system prerequisite and
cannot be made portable. Without it, some measurements are unavailable.

## Configuring
Choose a profile on the left. Add an action from the library on the right,
by clicking or dragging it onto the preview. Pages can be grouped into folders:
select a folder to see and edit its sub-pages. Click a key in the preview to
edit its settings below. **Size and behavior** sets the width, the height and the toggle mode. Technical options stay collapsed.
A keyboard shortcut can be recorded by pressing the keys together.
The Test button validates the command and its targets without running it.
In Settings, the About DeckEdge section shows the installed version,
the developer, the MIT license and the main components.

The preview runs no command. Save applies the changes to the phone.
Right-click lets you duplicate, move and delete. Ctrl+Z undoes.
Existing profiles open on Principal when it exists.

## Phone
The phone and the PC must be on the same private network. In the Studio,
click Connect phone, choose “This PC · permanent address” and
scan the QR code with the camera. Then add the opened page to
the home screen (Share on iPhone; browser menu on Android), or to your
bookmarks. The shortcut keeps the pairing: no new scan is needed
on each open. Changing the GitHub nickname and restarting the PC change
neither its permanent address nor its key.

The QR code and the link contain a private key: do not share them publicly.
If the network blocks local `.local` discovery, select the backup
Wi-Fi/Ethernet address on the QR screen. On that address, a change of IP
may require creating the shortcut again. The direct connection must stay on a
private network, with DeckEdge running on the PC.
Dragging vertically scrolls; dragging horizontally adjusts a slider.

## Sensors and audio
Accept the sensor engine's administrator access for full measurements.
If temperatures are missing on a new PC, install PawnIO from the DeckEdge
menu near the clock, then quit and restart DeckEdge. The original
driver is signed and shipped with the software; LibreHardwareMonitor must not be launched.
An audio application appears after creating a session: play a sound, then
refresh the outputs and applications in the settings of a volume slider.

## Troubleshooting
- Studio missing: start it again from the icon near the clock.
- Port 5000 in use: DeckEdge automatically picks the next port. If another
  copy of DeckEdge is already running, quit it before restarting.
- Phone unreachable: same network, full private link, private network firewall,
  no Wi-Fi client isolation. Do not open a port on the router.
- Blank Studio: install/repair Microsoft WebView2 Runtime from Microsoft.
- Logs: DeckEdge menu → View log / Open data.
- Deck language: `EN`/`FR` button to the right of the profile tabs on the phone.
- Before reporting: **Diagnostics** button in the Studio, then copy the redacted report.
- Before a major change: **Profiles** menu → **Local backups**. JSON export/import also keeps profiles off the PC.
- Quit completely before moving or replacing a portable version.
