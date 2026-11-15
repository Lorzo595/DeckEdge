# Third-party components distributed with DeckEdge

DeckEdge's own code is licensed under MIT (LICENSE). The following components
keep their own licenses; they are not covered by DeckEdge's MIT license.

- QRCoder 1.6.0, Raffael Herrmann, MIT: `QRCoder-LICENSE.txt`.
  Source: https://github.com/codebude/QRCoder/tree/bd980577640c47f8bb881cf24c8443415a579d36
  Used to generate QR codes locally, without an external service.

- LibreHardwareMonitorLib 0.9.6, unmodified, MPL-2.0.
  Exact sources: https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/tree/3d331e3370efb858411f19511373eff65a218701
  A copy of these sources is available in the package's `licenses/sources`.
  The bundled PawnIO modules keep their LGPL-2.1 license; their sources and
  rebuild instructions are listed in that same folder.
- .NET support libraries: versions, licenses and links to their sources in
  `licenses/dotnet`. They are redistributed unmodified and can be replaced by
  compatible versions in the DeckEdge folder.
- Microsoft WebView2 SDK 1.0.4314.35: Microsoft license included.
  The Evergreen WebView2 Runtime is a separate Windows prerequisite; the installer
  can launch its official installation if the Runtime is missing.
- Python 3.14.9: PSF license and notices in `runtime/LICENSE.txt`.
- Python modules: versions in requirements.txt and PYTHON-PACKAGES.json,
  original licenses in `runtime/Lib/site-packages/*.dist-info` and `licenses/python`.
- Local discovery: python-zeroconf 0.154.0, LGPL-2.1, with ifaddr 0.2.0.
  Exact zeroconf sources provided in `licenses/sources`; the modules remain
  replaceable by compatible versions.

Original sources and licenses are preserved; no third-party component changes
its author's name. DeckEdge is not an Elgato product and is not affiliated with Elgato.
