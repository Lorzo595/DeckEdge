# Security and local data

DeckEdge runs the shortcuts and applications you configure on your PC.
Use it on a trusted private network. It must not be exposed to the Internet
or placed behind a port forward. Local transport is HTTP, without TLS.

The Studio and configuration changes are only accessible from the PC.
The phone must use the full link provided in "Connect phone":
that link contains a private access key. Do not publish it. The browser remembers
the pairing in a cookie. To revoke all phones, quit DeckEdge,
delete `.phone-key` in the data folder and restart, then reconnect them.
An external web origin cannot use the server or its WebSockets.

The permanent `.local` name is derived from a PC identifier, without publishing that
raw identifier. mDNS discovery announces only the service name and port,
never the private key. The QR code is generated locally. The shortcut manifest
is reserved for paired devices, is not cached, and keeps the private link to
find the deck after a restart. Do not share this shortcut.

Data is stored in `%LOCALAPPDATA%\DeckEdge` for the installation,
or `data` next to DeckEdge.exe in portable mode. Discord tokens are local;
they must never be added to GitHub, screenshots or reports.
Uninstalling keeps profiles. Deliberately delete this folder
after uninstalling if you also want to erase your data.

To report a vulnerability, use the Security tab of the GitHub repository and
"Report a vulnerability" when it is enabled. Do not publish any secret in
a public issue. If this channel is not enabled, contact the repository owner
before publishing exploitable details.
