param([string]$OutputDirectory = '.build/update-e2e')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
. (Join-Path $PSScriptRoot 'test-output-path.ps1')
$output=Resolve-TestOutputPath -Root $root -Path $OutputDirectory
if(Test-Path -LiteralPath $output){Remove-Item -LiteralPath $output -Recurse -Force}
New-Item -ItemType Directory -Path $output -Force | Out-Null
$csc=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$stub=Join-Path $output 'Stub.exe'
& $csc /nologo /target:winexe /platform:x64 "/out:$stub" (Join-Path $root 'tests/UpdaterRestartStub.cs')
if($LASTEXITCODE -ne 0){throw 'Stub compilation failed.'}
$references=@('System.dll','System.Core.dll','System.Drawing.dll','System.Windows.Forms.dll','System.Web.Extensions.dll','System.IO.Compression.dll','System.IO.Compression.FileSystem.dll') | ForEach-Object {"/reference:$_"}
$helper=Join-Path $output 'DeckEdge.Updater.exe'
& $csc /nologo /target:winexe /platform:x64 /codepage:65001 "/out:$helper" @references (Join-Path $root 'desktop/UpdateEngine.cs') (Join-Path $root 'desktop/UpdaterMain.cs') (Join-Path $root 'desktop/UiText.cs')
if($LASTEXITCODE -ne 0){throw 'Helper compilation failed.'}
Add-Type -AssemblyName System.IO.Compression.FileSystem
foreach($portable in @($false,$true)){
    $edition=if($portable){'portable'}else{'installed'}
    $target=Join-Path $output "$edition with spaces"
    $payload=Join-Path $output "$edition-payload/DeckEdge"
    $work=Join-Path ([IO.Path]::GetTempPath()) ('DeckEdge-update-'+[Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $target,(Join-Path $target 'data'),(Join-Path $payload 'runtime'),$work -Force | Out-Null
    Copy-Item -LiteralPath $stub -Destination (Join-Path $target 'DeckEdge.exe')
    Copy-Item -LiteralPath $stub -Destination (Join-Path $payload 'DeckEdge.exe')
    Copy-Item -LiteralPath $helper -Destination $work
    '0.1.4' | Set-Content -LiteralPath (Join-Path $target 'VERSION') -Encoding ascii
    '0.1.5' | Set-Content -LiteralPath (Join-Path $payload 'VERSION') -Encoding ascii
    'server old' | Set-Content -LiteralPath (Join-Path $target 'desktop_backend.py')
    'server new' | Set-Content -LiteralPath (Join-Path $payload 'desktop_backend.py')
    'fake runtime' | Set-Content -LiteralPath (Join-Path $payload 'runtime/python.exe')
    'payload marker' | Set-Content -LiteralPath (Join-Path $payload 'portable.flag')
    if($portable){'original marker' | Set-Content -LiteralPath (Join-Path $target 'portable.flag')}
    'profile fixture' | Set-Content -LiteralPath (Join-Path $target 'data/config.json')
    'phone fixture' | Set-Content -LiteralPath (Join-Path $target 'data/.phone-key')
    $profile=(Get-FileHash -LiteralPath (Join-Path $target 'data/config.json')).Hash
    $phone=(Get-FileHash -LiteralPath (Join-Path $target 'data/.phone-key')).Hash
    $zip=Join-Path $work 'package.zip'
    [IO.Compression.ZipFile]::CreateFromDirectory((Split-Path -Parent $payload),$zip)
    $old=Start-Process -FilePath (Join-Path $target 'DeckEdge.exe') -ArgumentList '--wait' -WindowStyle Hidden -PassThru
    $data=Join-Path $target 'data'
    @{Target=$target;Version='0.1.5';Sha256=(Get-FileHash $zip).Hash.ToLowerInvariant();Portable=$portable;ProcessId=$old.Id;ProcessStart=$old.StartTime.ToUniversalTime().Ticks;Language='en';DataDirectory=$data} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $work 'plan.json') -Encoding utf8
    $updater=Start-Process -FilePath (Join-Path $work 'DeckEdge.Updater.exe') -ArgumentList ('"'+(Join-Path $work 'plan.json')+'"') -WindowStyle Hidden -PassThru
    if(-not $updater.WaitForExit(20000)){throw "Updater did not finish; inspect $work"}
    $marker=Join-Path $target 'restart.marker'
    for($i=0;$i -lt 30 -and -not(Test-Path $marker);$i++){Start-Sleep -Milliseconds 100}
    if(-not(Test-Path $marker) -or (Get-Content $marker -Raw) -ne $data){throw "Restart/data directory not preserved; inspect $work"}
    if((Get-Content (Join-Path $target 'VERSION') -Raw).Trim() -ne '0.1.5'){throw 'Version not updated'}
    if((Get-FileHash (Join-Path $target 'data/config.json')).Hash -ne $profile -or (Get-FileHash (Join-Path $target 'data/.phone-key')).Hash -ne $phone){throw 'User data changed'}
    if((Test-Path (Join-Path $target 'portable.flag')) -ne $portable){throw 'Edition changed'}
    if(Test-Path (Join-Path $work 'error.txt')){throw "Updater reported an error: $work"}
    Write-Output "OK: $edition helper handoff, process wait, verified replacement, restart, profile/phone key and data directory preserved."
}
