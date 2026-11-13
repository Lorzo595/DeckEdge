param([string]$OutputDirectory, [string]$HardwareDirectory, [switch]$NoShortcut)
$ErrorActionPreference = 'Stop'
$desktopDir = $PSScriptRoot
$projectDir = Split-Path -Parent $desktopDir
$workspaceDir = Split-Path -Parent $projectDir
$sdkVersion = '1.0.4314.35'
$sdkDir = Join-Path $desktopDir 'vendor/webview2'
$outputDir = Join-Path $desktopDir 'bin'
if ($OutputDirectory) { $outputDir = [System.IO.Path]::GetFullPath($OutputDirectory) }
if (-not $HardwareDirectory) {
    $HardwareDirectory = Join-Path $projectDir '.build/lhm'
    if (-not (Test-Path -LiteralPath (Join-Path $HardwareDirectory 'LibreHardwareMonitorLib.dll'))) {
        & (Join-Path $projectDir 'packaging/prepare-dependencies.ps1')
    }
}
if (-not (Test-Path -LiteralPath (Join-Path $sdkDir 'lib/net462/Microsoft.Web.WebView2.WinForms.dll'))) {
    $archivePath = Join-Path $desktopDir 'vendor/webview2.zip'
    New-Item -ItemType Directory -Path (Split-Path -Parent $archivePath) -Force | Out-Null
    Invoke-WebRequest -Uri "https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/$sdkVersion/microsoft.web.webview2.$sdkVersion.nupkg" -OutFile $archivePath
    Expand-Archive -LiteralPath $archivePath -DestinationPath $sdkDir -Force
}
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
# Icône dessinée localement, commune à la fenêtre, à la barre des tâches et au raccourci.
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class DeckEdgeIconInterop {
    [DllImport("user32.dll")] public static extern bool DestroyIcon(IntPtr icon);
}
'@
$bitmap = New-Object System.Drawing.Bitmap 64,64
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.Clear([System.Drawing.Color]::FromArgb(27,29,26))
$amberBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(223,185,121))
$amberPen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(223,185,121)),3
$graphics.DrawRectangle($amberPen,10,9,44,46)
$graphics.FillRectangle($amberBrush,10,9,11,46)
$graphics.FillRectangle($amberBrush,32,20,12,4)
$graphics.FillRectangle($amberBrush,32,40,12,4)
$iconHandle = $bitmap.GetHicon()
$icon = [System.Drawing.Icon]::FromHandle($iconHandle)
$iconFile = Join-Path $desktopDir 'DeckEdge.ico'
$stream = [System.IO.File]::Create($iconFile)
try { $icon.Save($stream) } finally {
    $stream.Dispose(); $icon.Dispose(); [DeckEdgeIconInterop]::DestroyIcon($iconHandle) | Out-Null
    $graphics.Dispose(); $bitmap.Dispose(); $amberBrush.Dispose(); $amberPen.Dispose()
}
$cscPath = Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$appPath = Join-Path $outputDir 'DeckEdge.exe'
$references = @('System.dll','System.Core.dll','System.Drawing.dll','System.Windows.Forms.dll','System.Web.Extensions.dll','System.Xml.dll','System.Security.dll',
    (Join-Path $HardwareDirectory 'LibreHardwareMonitorLib.dll'),
    (Join-Path $sdkDir 'lib/net462/Microsoft.Web.WebView2.Core.dll'),
    (Join-Path $sdkDir 'lib/net462/Microsoft.Web.WebView2.WinForms.dll'))
$compilerArgs = @('/nologo','/target:winexe','/platform:x64','/optimize+', '/codepage:65001',
    "/out:$appPath", "/win32icon:$iconFile", "/win32manifest:$(Join-Path $desktopDir 'app.manifest')")
$compilerArgs += $references | ForEach-Object { "/reference:$_" }
$compilerArgs += Join-Path $desktopDir 'DeckEdge.cs'
$compilerArgs += Join-Path $desktopDir 'SensorHost.cs'
$compilerArgs += Join-Path $desktopDir 'AppSettings.cs'
$compilerArgs += Join-Path $desktopDir 'ScreenColorPicker.cs'
$compilerArgs += Join-Path $desktopDir 'AssemblyInfo.cs'
& $cscPath $compilerArgs
if ($LASTEXITCODE -ne 0) { throw 'La compilation de DeckEdge a échoué.' }
Copy-Item -LiteralPath (Join-Path $desktopDir 'LibreHardwareMonitor-LICENSE.txt'),(Join-Path $desktopDir 'THIRD-PARTY-NOTICES.md') -Destination $outputDir -Force
Get-ChildItem -LiteralPath $HardwareDirectory -Filter '*.dll' |
    Where-Object { $_.Name -notin @('Aga.Controls.dll','OxyPlot.dll','OxyPlot.WindowsForms.dll') } |
    Copy-Item -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $sdkDir 'lib/net462/Microsoft.Web.WebView2.Core.dll'),(Join-Path $sdkDir 'lib/net462/Microsoft.Web.WebView2.WinForms.dll'),(Join-Path $sdkDir 'runtimes/win-x64/native/WebView2Loader.dll') -Destination $outputDir -Force
Copy-Item -LiteralPath (Join-Path $sdkDir 'LICENSE.txt') -Destination (Join-Path $outputDir 'WebView2-LICENSE.txt') -Force
@'
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <startup><supportedRuntime version="v4.0" sku=".NETFramework,Version=v4.7.2" /></startup>
</configuration>
'@ | Set-Content -LiteralPath (Join-Path $outputDir 'DeckEdge.exe.config') -Encoding utf8
if (-not $NoShortcut) {
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path $workspaceDir 'DeckEdge.lnk'))
$shortcut.TargetPath = $appPath
$shortcut.WorkingDirectory = $projectDir
$shortcut.IconLocation = "$appPath,0"
$shortcut.Description = 'DeckEdge — Studio, serveur et capteurs'
$shortcut.Save()
Write-Output "Application prête : $appPath"
Write-Output "Raccourci : $(Join-Path $workspaceDir 'DeckEdge.lnk')"
}
