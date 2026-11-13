param([string]$Destination)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
if (-not $Destination) { $Destination=Join-Path $root '.build/source/DeckEdge' }
$Destination=[IO.Path]::GetFullPath($Destination)
if (Test-Path -LiteralPath $Destination) { throw "Le dossier source existe déjà : $Destination. Utilisez un nouveau dossier pour éviter de mélanger des données." }
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$files=@('admin.html','index.html','app_paths.py','network_access.py','audio_sessions.py','desktop_backend.py','discord_rpc.py','monitoring.py','server.py','deck-layout.css','deck-layout.js','studio.js','studio-colors.js','studio-shell.js','studio-shell.css','requirements.txt','README.md','LICENSE','VERSION','.gitignore','SECURITY.md','CONTRIBUTING.md','CHANGELOG.md')
foreach($file in $files) { Copy-Item -LiteralPath (Join-Path $root $file) -Destination $Destination }
foreach($directory in @('desktop','packaging','tests','docs','.github')) {
    $base=Join-Path $root $directory
    foreach($file in Get-ChildItem -LiteralPath $base -Recurse -File) {
        $relative=$file.FullName.Substring($base.Length+1)
        if($relative -match '(^|[\\/])(bin|vendor|__pycache__)([\\/]|$)' -or $file.Extension -in @('.pyc','.exe','.dll','.zip','.ico','.png','.log')) {continue}
        $target=Join-Path (Join-Path $Destination $directory) $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $target
    }
}
Write-Output "Sources publiques uniquement : $Destination"
