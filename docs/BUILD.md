# Building DeckEdge on Windows

All tracked text files use LF in both the Git index and the working tree, even
on Windows. `.gitattributes` enforces checkout/staging and `.editorconfig` sets
editor defaults. Run `python tests/check_line_endings.py` before publishing;
CI checks it too. Upload LF files only when bypassing `git add` through a web UI.

## Environment

Windows x64, .NET Framework 4.8, PowerShell 5.1 or 7, HTTPS access to Python.org,
PyPI, NuGet and GitHub. The .NET Framework C# compiler is used; Visual
Studio is not required. Git and Node.js are only needed to contribute
or to run the browser tests. The software targets Windows 10 build 19041+ / Windows 11.

## One command for the three distributions

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build-release.ps1
```

The script downloads components into `.build`, checks the hashes
in `packaging/dependencies.json`, creates the embedded Python 3.14.9 and its locked
dependencies, compiles the Studio and builds the archives and the installer.
It installs the Inno Setup compiler into `.build/tools/InnoSetup` for the current
user when needed. No build tool is installed inside the portable build.
You can supply an already installed Inno Setup with `-IsccPath "...\ISCC.exe"`.
`-PortableOnly` skips the Inno Setup installation and produces no Setup.exe.

Outputs go to `dist`. `.build/latest-release.json` points to the portable
folder and the cleaned sources folder. Preparation folders are
new on every build to avoid reintroducing old data.
The scripts never delete the developer machine's configuration.

The embedded runtime is isolated by `python314._pth`; its path to the server
stays relative. Libraries are copied without Python caches or installation
scripts containing absolute paths. `--check` tests the server with
temporary data. The Python tests run before the installer.

Sensor components are downloaded from LibreHardwareMonitor 0.9.6,
never from an LHM application installed next to the project. The notices and the
exact sources of LibreHardwareMonitor, PawnIO.Modules and PawnIO are included.
.NET licenses come from the matching NuGet packages, and Python
licenses from the installed distributions. The WebView2 bootstrapper is verified
by its Microsoft Authenticode signature; its Evergreen version may change.

Direct and transitive dependencies are locked in requirements.txt.
The hashes do not make the build bit-for-bit reproducible:
timestamps, prerequisite signatures and tools may vary. The get-pip
bootstrap is pinned to an official commit. Any SHA256 failure stops the build;
check the origin, update the manifest and test before a new release.

## Checks

```powershell
packaging\check-release.ps1
.venv\Scripts\python.exe -m unittest discover -s tests -t . -p "test_*.py"
```

The network tests check key-based pairing, the private cookie, refusal of
remote administration and WebSocket origins. The existing tests cover
audio, the startup profile, widget sizes, monitoring, persistence and
command regressions.

The C# preferences test checks the defaults, the migration and
atomic writes without changing the Windows startup registration:

```powershell
powershell -ExecutionPolicy Bypass -File tests\run-csharp-smoke.ps1
```

After quitting every copy of DeckEdge, `packaging/smoke-test.ps1` extracts
the portable build into a path containing spaces, launches it with a PATH without
Python, and checks the server, the limited sensors, the backup and the shutdown.
`-IncludeInstaller` also tests installation and uninstallation in `.build`,
with isolated data and without enabling automatic startup. This option
refuses to run if DeckEdge is already installed for the current user.
This local test does not replace validation in a clean Windows VM.

The browser tests require Node.js, Playwright and Edge. To install them
without adding a production dependency: `npm install --no-save playwright`.
The following script starts an isolated server on `127.0.0.1:5011`, runs the fifteen
Studio/mobile tests and shuts down cleanly:

```powershell
powershell -ExecutionPolicy Bypass -File tests\run-ui-tests.ps1
```

The tests covered are `studio-shell`, `studio-ergonomics`, `studio-colors`,
`mobile-preview`, `mobile-gestures`, `startup-profile`, `diagnostics`, `profiles`,
`sequences`, `studio-actions`, `mobile-accessibility`, `folders`, `phones`, `i18n` and `studio-i18n`.
The script accepts `-Port` and `-DataDirectory` to isolate the data; the data
folder must stay under `.build`. To run a manual test, set
`DECKEDGE_TEST_URL` to the test server.

The Studio tests intercept profiles and backups; they must not
modify the real profiles. Never enable a real command to test
a visual change. For a final validation, test the installation and
uninstallation on a clean Windows VM, then the portable build moved into a
path containing spaces. Check a PC without Python and, if possible, without
WebView2/PawnIO for the prerequisite installation flows.

## Running from source

Create a Python environment with requirements.txt, then run `desktop/build.ps1`.
The Studio looks for a compatible Python in the user installations and PATH.
Data stays in the project during development. You can also run
`python server.py` for the server alone; the built-in sensors require the Studio.

For an isolated test: set `DECKEDGE_DATA_DIR` before starting the Python server.
The native development build keeps the project's existing data.

## Changing the version

Update VERSION, both version attributes in desktop/AssemblyInfo.cs,
CHANGELOG.md and docs/RELEASE-NOTES.md. Rebuild, check the archives and
test the executables before creating the matching GitHub tag.
