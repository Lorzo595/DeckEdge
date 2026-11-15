param([string]$OutputDirectory = '.build/update-ui-smoke')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
. (Join-Path $PSScriptRoot 'test-output-path.ps1')
$output=Resolve-TestOutputPath -Root $root -Path $OutputDirectory
if(Test-Path -LiteralPath $output){Remove-Item -LiteralPath $output -Recurse -Force}
New-Item -ItemType Directory -Path $output -Force | Out-Null
$csc=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$references=@('System.dll','System.Core.dll','System.Drawing.dll','System.Windows.Forms.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll') | ForEach-Object {"/reference:$_"}
$exe=Join-Path $output 'UpdatesUiSmoke.exe'
$sources=@('desktop/UpdateEngine.cs','desktop/Updates.cs','desktop/UiText.cs','desktop/AssemblyInfo.cs','tests/UpdatesUiSmoke.cs') | ForEach-Object {Join-Path $root $_}
& $csc /nologo /target:exe /platform:x64 /codepage:65001 "/out:$exe" @references @sources
if($LASTEXITCODE -ne 0){throw 'Update UI test compilation failed.'}
& $exe $output
if($LASTEXITCODE -ne 0){throw 'Update UI checks failed.'}
