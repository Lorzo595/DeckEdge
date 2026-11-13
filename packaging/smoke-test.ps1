param([switch]$IncludeInstaller)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$version=(Get-Content VERSION -Raw).Trim()
try{$null=Invoke-RestMethod 'http://127.0.0.1:5000/api/health' -TimeoutSec 2;throw 'Quittez la copie de DeckEdge en cours avant ce test.'}
catch{if($_.Exception.Message -like 'Quittez*'){throw}}
if($IncludeInstaller -and (Test-Path 'HKCU:/Software/Microsoft/Windows/CurrentVersion/Uninstall/{4A8E0309-846A-4E17-827B-8154D77C4060}_is1')){throw 'Une installation DeckEdge existe. Testez dans une VM ou utilisez uniquement le test portable.'}
$testRoot=Join-Path $root ('.build/Distribution test '+[Guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
function Invoke-ApplicationTest([string]$Directory,[string]$Data,[bool]$OverrideData){
    New-Item -ItemType Directory -Path $Data -Force | Out-Null
    @{FullSensorAccess=$false;KeepAwake=$false;CloseToTray=$true;WindowWidth=1100;WindowHeight=820;StartWithWindows=$false} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $Data 'app-settings.json')
    $exe=Join-Path $Directory 'DeckEdge.exe'
    $info=New-Object Diagnostics.ProcessStartInfo
    $info.FileName=$exe;$info.WorkingDirectory=$Directory;$info.UseShellExecute=$false
    $info.EnvironmentVariables['PATH']=(Join-Path $env:WINDIR 'System32')
    if($OverrideData){$info.EnvironmentVariables['DECKEDGE_DATA_DIR']=$Data}else{$info.EnvironmentVariables.Remove('DECKEDGE_DATA_DIR')}
    $app=[Diagnostics.Process]::Start($info)
    try{
        $health=$null
        for($attempt=0;$attempt -lt 100;$attempt++){
            try{$health=Invoke-RestMethod 'http://127.0.0.1:5000/api/health' -TimeoutSec 1}catch{}
            if($health -and $health.monitoring.connected){break}
            if($app.HasExited){throw 'Application quittée au démarrage.'}
            Start-Sleep -Milliseconds 400
        }
        if(-not $health -or -not $health.monitoring.connected){throw 'Serveur ou capteurs indisponibles après 40 secondes.'}
        $backend=Get-CimInstance Win32_Process | Where-Object {$_.ParentProcessId -eq $app.Id -and $_.Name -eq 'python.exe'}
        if(-not $backend -or $backend.ExecutablePath -ne (Join-Path $Directory 'runtime/python.exe').Replace('/','\')){throw 'Le serveur utilise un Python extérieur au paquet.'}
        $null=Invoke-WebRequest 'http://127.0.0.1:5000/admin' -UseBasicParsing
        $config=Invoke-RestMethod 'http://127.0.0.1:5000/api/config'
        $config.pages[0].buttons[0].label='Test distribution'
        $json=$config | ConvertTo-Json -Depth 20
        $null=Invoke-RestMethod 'http://127.0.0.1:5000/api/config' -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($json))
        $saved=Get-Content (Join-Path $Data 'config.json') -Raw | ConvertFrom-Json
        if($saved.pages[0].buttons[0].label -ne 'Test distribution'){throw 'Sauvegarde dans le dossier de données incorrecte.'}
        if(-not(Test-Path (Join-Path $Data '.phone-key'))){throw 'Clé de téléphone absente.'}
        Write-Output ('OK : lancement, Python embarqué sans PATH Python, Studio, sauvegarde et '+$health.monitoring.sensors_count+' capteurs en accès limité.')
    }finally{
        $quitInfo=New-Object Diagnostics.ProcessStartInfo
        $quitInfo.FileName=$exe;$quitInfo.Arguments='--quit';$quitInfo.UseShellExecute=$false;$quitInfo.CreateNoWindow=$true
        if($OverrideData){$quitInfo.EnvironmentVariables['DECKEDGE_DATA_DIR']=$Data}
        $quit=[Diagnostics.Process]::Start($quitInfo);$quit.WaitForExit();$quit.Dispose()
        if(-not $app.WaitForExit(15000)){throw 'DeckEdge ne se ferme pas proprement.'}
        $app.Dispose()
    }
    for($attempt=0;$attempt -lt 40;$attempt++){
        try{$null=Invoke-RestMethod 'http://127.0.0.1:5000/api/health' -TimeoutSec 1;Start-Sleep -Milliseconds 250}catch{break}
    }
}
$unpacked=Join-Path $testRoot 'Portable déplacé'
Expand-Archive -LiteralPath (Join-Path $root "dist/DeckEdge-$version-Portable-x64.zip") -DestinationPath $unpacked
$portable=Join-Path $unpacked 'DeckEdge'
Invoke-ApplicationTest $portable (Join-Path $portable 'data') $false
if($IncludeInstaller){
    $installed=Join-Path $testRoot 'Installation classique'
    $installer=Join-Path $root "dist/DeckEdge-$version-Setup-x64.exe"
    $process=Start-Process -FilePath $installer -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOICONS','/TASKS=',('/DIR="'+$installed+'"'),('/LOG="'+(Join-Path $testRoot 'setup.log')+'"')) -WindowStyle Hidden -PassThru -Wait
    if($process.ExitCode -ne 0){throw 'Installation silencieuse en échec.'}
    if(Test-Path (Join-Path $installed 'portable.flag')){throw 'Le mode installé ne doit pas avoir portable.flag.'}
    $data=Join-Path $testRoot 'Données installées isolées'
    Invoke-ApplicationTest $installed $data $true
    $resolved=[IO.Path]::GetFullPath($installed)
    if(-not $resolved.StartsWith([IO.Path]::GetFullPath($testRoot)+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Dossier de désinstallation hors du test.'}
    $uninstaller=Join-Path $installed 'unins000.exe'
    $process=Start-Process -FilePath $uninstaller -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="'+(Join-Path $testRoot 'uninstall.log')+'"')) -WindowStyle Hidden -PassThru -Wait
    if($process.ExitCode -ne 0){throw 'Désinstallation en échec.'}
    if(Test-Path (Join-Path $installed 'DeckEdge.exe')){throw 'Exécutable conservé après désinstallation.'}
    if(-not(Test-Path (Join-Path $data 'config.json'))){throw 'Les profils doivent être conservés.'}
    if(Test-Path 'HKCU:/Software/Microsoft/Windows/CurrentVersion/Uninstall/{4A8E0309-846A-4E17-827B-8154D77C4060}_is1'){throw 'Entrée de désinstallation conservée.'}
    Write-Output 'OK : installation, fonctionnement en mode installé, désinstallation et conservation des profils.'
}
Write-Output "Données de test isolées : $testRoot"
