param([switch]$IncludeInstaller)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$cache = Join-Path $root '.build/cache'
New-Item -ItemType Directory -Path $cache -Force | Out-Null
$manifest = Get-Content (Join-Path $PSScriptRoot 'dependencies.json') -Raw | ConvertFrom-Json
function Receive-Checked($Name, $File) {
    $asset = $manifest.$Name
    $path = Join-Path $cache $File
    if (-not (Test-Path -LiteralPath $path)) { Invoke-WebRequest -Uri $asset.url -OutFile $path -UseBasicParsing }
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $asset.sha256) { throw "SHA256 incorrect : $Name. Supprimez le fichier de cache et vérifiez la source avant de relancer." }
    return $path
}
$qr = Receive-Checked 'qrcoder' 'qrcoder.zip'
if (-not (Test-Path (Join-Path $root 'desktop/vendor/qrcoder/lib/net40/QRCoder.dll'))) { Expand-Archive -LiteralPath $qr -DestinationPath (Join-Path $root 'desktop/vendor/qrcoder') -Force }
$lhm = Receive-Checked 'lhm' 'lhm.zip'
if (-not (Test-Path (Join-Path $root '.build/lhm/LibreHardwareMonitorLib.dll'))) { Expand-Archive -LiteralPath $lhm -DestinationPath (Join-Path $root '.build/lhm') -Force }
$null = Receive-Checked 'python' 'python.zip'
$null = Receive-Checked 'get-pip' 'get-pip.py'
$webview = Receive-Checked 'webview2' 'webview2.zip'
if (-not (Test-Path (Join-Path $root 'desktop/vendor/webview2/LICENSE.txt'))) { Expand-Archive -LiteralPath $webview -DestinationPath (Join-Path $root 'desktop/vendor/webview2') -Force }
if ($IncludeInstaller) {
    $installer = Receive-Checked 'innosetup' 'innosetup.exe'
    $tools = Join-Path $root '.build/tools/InnoSetup'
    if (-not (Test-Path (Join-Path $tools 'ISCC.exe'))) {
        $process = Start-Process -FilePath $installer -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER','/NOICONS','/TASKS=',('/DIR="' + $tools + '"')) -WindowStyle Hidden -PassThru -Wait
        if ($process.ExitCode -ne 0) { throw 'Installation du compilateur Inno Setup impossible.' }
    }
}
Write-Output 'Dépendances téléchargées et empreintes vérifiées.'
