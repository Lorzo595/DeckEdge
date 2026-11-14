param([string]$IsccPath, [switch]$PortableOnly)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$version=(Get-Content VERSION -Raw).Trim()
if($version -notmatch '^\d+\.\d+\.\d+$'){throw 'VERSION doit contenir un numéro x.y.z.'}
$assembly=Get-Content desktop/AssemblyInfo.cs -Raw
if($assembly -notmatch ('AssemblyFileVersion\("'+[regex]::Escape($version)+'\.0"\)')){throw 'VERSION et AssemblyInfo.cs doivent correspondre.'}
& "$PSScriptRoot/prepare-dependencies.ps1" -IncludeInstaller:(-not $PortableOnly -and -not $IsccPath)
$runtime=Join-Path $root '.build/runtime'
if(-not(Test-Path (Join-Path $runtime 'python.exe'))){Expand-Archive -LiteralPath '.build/cache/python.zip' -DestinationPath $runtime -Force}
@'
python314.zip
.
Lib\site-packages
..\..
import site
'@ | Set-Content -Encoding ascii (Join-Path $runtime 'python314._pth')
$python=Join-Path $runtime 'python.exe'
& $python '.build/cache/get-pip.py' 'pip==26.3' --disable-pip-version-check
if($LASTEXITCODE -ne 0){throw 'Installation de pip impossible.'}
& $python -m pip install --disable-pip-version-check --no-warn-script-location setuptools==80.9.0 wheel==0.45.1
if($LASTEXITCODE -ne 0){throw 'Installation des outils Python impossible.'}
& $python -m pip install --disable-pip-version-check --no-warn-script-location --no-build-isolation -r requirements.txt
if($LASTEXITCODE -ne 0){throw 'Installation des dépendances Python impossible.'}
& $python -m pip check
if($LASTEXITCODE -ne 0){throw 'Dépendances Python incompatibles.'}
$stamp=[DateTime]::Now.ToString('yyyyMMdd-HHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,6)
$stage=Join-Path $root ('.build/package-'+$stamp+'/DeckEdge')
New-Item -ItemType Directory -Path $stage -Force | Out-Null
& "$root/desktop/build.ps1" -OutputDirectory (Join-Path $root '.build/native') -HardwareDirectory (Join-Path $root '.build/lhm') -NoShortcut
Copy-Item -Path '.build/native/*' -Destination $stage -Recurse
$resources=@('admin.html','index.html','app_paths.py','network_access.py','local_discovery.py','audio_sessions.py','desktop_backend.py','discord_rpc.py','monitoring.py','server.py','deck-layout.css','deck-layout.js','studio.js','studio-colors.js','studio-shell.js','studio-shell.css','requirements.txt','LICENSE','VERSION','SECURITY.md')
foreach($file in $resources){Copy-Item -LiteralPath (Join-Path $root $file) -Destination $stage}
Copy-Item -LiteralPath 'docs/QUICKSTART.md' -Destination (Join-Path $stage 'LIRE-MOI.md')
Copy-Item -LiteralPath 'docs/QUICKSTART.md' -Destination (Join-Path $stage 'README.md')
$runtimeTarget=Join-Path $stage 'runtime'
foreach($file in Get-ChildItem -LiteralPath $runtime -Recurse -File){
    $relative=$file.FullName.Substring($runtime.Length+1)
    if($relative -match '(^|[\\/])(__pycache__|Scripts)([\\/]|$)' -or $file.Extension -in @('.pyc','.pyo')){continue}
    if($relative -match '^Lib[\\/]site-packages[\\/]comtypes[\\/]gen[\\/]' -and $file.Name -ne '__init__.py'){continue}
    $target=Join-Path $runtimeTarget $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $target
}
@'
python314.zip
.
Lib\site-packages
..
import site
'@ | Set-Content -Encoding ascii (Join-Path $runtimeTarget 'python314._pth')
$prerequisites=Join-Path $stage 'prerequisites';New-Item -ItemType Directory -Path $prerequisites -Force | Out-Null
$webview=Join-Path $root '.build/cache/MicrosoftEdgeWebview2Setup.exe'
if(-not(Test-Path $webview)){Invoke-WebRequest 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile $webview -UseBasicParsing}
$signature=Get-AuthenticodeSignature -LiteralPath $webview
if($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation'){throw 'Signature Microsoft du bootstrapper WebView2 non valide.'}
Copy-Item $webview -Destination $prerequisites
$pawn=Join-Path $root '.build/cache/PawnIO_setup.exe'
if(-not(Test-Path $pawn)){Invoke-WebRequest 'https://raw.githubusercontent.com/LibreHardwareMonitor/LibreHardwareMonitor/3d331e3370efb858411f19511373eff65a218701/LibreHardwareMonitor/Resources/PawnIO_setup.exe' -OutFile $pawn -UseBasicParsing}
if((Get-FileHash $pawn).Hash -ne 'A3A46226C5E2824F4CDD42BE0EECBABFC672C86F7889710F5AB1E6AD385B47A0'){throw 'SHA256 PawnIO incorrect.'}
if((Get-AuthenticodeSignature $pawn).Status -ne 'Valid'){throw 'Signature du pilote PawnIO non valide.'}
Copy-Item $pawn -Destination $prerequisites
$licenseCache=Join-Path $root '.build/licenses'
& "$PSScriptRoot/collect-licenses.ps1" -Destination $licenseCache
Copy-Item -LiteralPath $licenseCache -Destination (Join-Path $stage 'licenses') -Recurse
& $python "$PSScriptRoot/python-licenses.py" (Join-Path $stage 'licenses/python')
if($LASTEXITCODE -ne 0){throw 'Export des licences Python impossible.'}
# All checks use a private, disposable data directory outside the shipped payload.
$previousData=$env:DECKEDGE_DATA_DIR
try {
    $env:DECKEDGE_DATA_DIR=Join-Path $root ('.build/check-'+$stamp)
    & (Join-Path $runtimeTarget 'python.exe') -B (Join-Path $stage 'desktop_backend.py') --check
    if($LASTEXITCODE -ne 0){throw 'Le serveur autonome ne démarre pas.'}
    & $python -m unittest discover -s tests -t . -p 'test_*.py'
    if($LASTEXITCODE -ne 0){throw 'Tests Python en échec.'}
} finally {$env:DECKEDGE_DATA_DIR=$previousData}
$dist=Join-Path $root 'dist';New-Item -ItemType Directory -Path $dist -Force | Out-Null
if(-not $PortableOnly){
    if(-not $IsccPath){$IsccPath=Join-Path $root '.build/tools/InnoSetup/ISCC.exe'}
    if(-not(Test-Path -LiteralPath $IsccPath)){throw 'Compilateur Inno Setup absent. Indiquez -IsccPath.'}
    & $IsccPath /Qp "/DAppVersion=$version" "/DPayload=$stage" "/DOutput=$dist" "$PSScriptRoot/DeckEdge.iss"
    if($LASTEXITCODE -ne 0){throw 'Compilation de lʼinstallateur en échec.'}
}
'DeckEdge portable: keep this file next to DeckEdge.exe.' | Set-Content -Encoding ascii (Join-Path $stage 'portable.flag')
$source=Join-Path $root ('.build/source-'+$stamp+'/DeckEdge')
& "$PSScriptRoot/export-source.ps1" -Destination $source
Compress-Archive -LiteralPath $stage -DestinationPath (Join-Path $dist "DeckEdge-$version-Portable-x64.zip") -Force
# ZipArchive includes dotfiles (.github/.gitignore) reliably on PowerShell 5.1.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$sourceZip=Join-Path $dist "DeckEdge-$version-Source.zip"
if(Test-Path -LiteralPath $sourceZip){Remove-Item -LiteralPath $sourceZip -Force}
[IO.Compression.ZipFile]::CreateFromDirectory((Split-Path -Parent $source),$sourceZip)
Get-ChildItem $dist -File | Where-Object {$_.Name -like "DeckEdge-$version-*"} | ForEach-Object {
    (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()+'  '+$_.Name
} | Set-Content -Encoding ascii (Join-Path $dist 'SHA256SUMS.txt')
@{version=$version;portable=$stage;source=$source} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $root '.build/latest-release.json')
Write-Output "Distribution prête : $dist"
Write-Output "Dossier de sources à publier : $source"
