param([string]$OutputDirectory = '.build/csharp-smoke')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
. (Join-Path $PSScriptRoot 'test-output-path.ps1')

$csc = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
if (-not (Test-Path -LiteralPath $csc)) { throw 'Compilateur C# .NET Framework introuvable.' }

$output = Resolve-TestOutputPath -Root $root -Path $OutputDirectory
Remove-Item -LiteralPath $output -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $output -Force | Out-Null
$exe = Join-Path $output 'SettingsSmoke.exe'

$references = @(
    'System.dll', 'System.Core.dll', 'System.Drawing.dll', 'System.Windows.Forms.dll',
    'System.Web.Extensions.dll', 'System.Security.dll'
) | ForEach-Object { '/reference:' + $_ }

$appSettings = Join-Path $root 'desktop/AppSettings.cs'
$uiText = Join-Path $root 'desktop/UiText.cs'
$settingsSmoke = Join-Path $root 'tests/SettingsSmoke.cs'
& $csc /nologo /target:exe /platform:x64 /codepage:65001 "/out:$exe" @references $appSettings $uiText $settingsSmoke
if ($LASTEXITCODE -ne 0) { throw 'Compilation du test C# des préférences impossible.' }

& $exe $output
if ($LASTEXITCODE -ne 0) { throw 'Test C# des préférences en échec.' }
