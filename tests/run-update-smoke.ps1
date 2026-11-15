param([string]$OutputDirectory = '.build/update-smoke')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
. (Join-Path $PSScriptRoot 'test-output-path.ps1')
$output=Resolve-TestOutputPath -Root $root -Path $OutputDirectory
if(Test-Path -LiteralPath $output){Remove-Item -LiteralPath $output -Recurse -Force}
New-Item -ItemType Directory -Path $output -Force | Out-Null
$csc=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$references=@('System.dll','System.Core.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll') | ForEach-Object {"/reference:$_"}
$exe=Join-Path $output 'UpdatesSmoke.exe'
& $csc /nologo /target:exe /platform:x64 /codepage:65001 "/out:$exe" @references (Join-Path $root 'desktop/UpdateEngine.cs') (Join-Path $root 'tests/UpdatesSmoke.cs')
if($LASTEXITCODE -ne 0){throw 'Updater test compilation failed.'}
& $exe (Join-Path $output 'fixtures')
if($LASTEXITCODE -ne 0){throw 'Updater tests failed.'}
