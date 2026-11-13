param([string]$DistributionDirectory)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
if(-not $DistributionDirectory){$DistributionDirectory=Join-Path $root 'dist'}
$version=(Get-Content (Join-Path $root 'VERSION') -Raw).Trim()
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archives=@("DeckEdge-$version-Portable-x64.zip","DeckEdge-$version-Source.zip")
foreach($name in $archives){
    $archive=[IO.Compression.ZipFile]::OpenRead((Join-Path $DistributionDirectory $name))
    try{
        $entries=@($archive.Entries | ForEach-Object {$_.FullName.Replace('\','/')})
        foreach($entry in $entries){
            if($entry -match '(^|/)(\.desktop-profile|__pycache__|\.git|\.build)/' -or $entry -match '^DeckEdge/data/' -or $entry -match '(^|/)(discord_config\.json|app-settings\.json|config_safe_backup\.json|config\.json(\.bak|\.tmp)?|\.phone-key|\.device-id|.*\.log|.*\.lnk)$'){
                throw "Fichier privé ou temporaire dans $name : $entry"
            }
        }
        if($name -like '*Source.zip'){
            foreach($required in @('DeckEdge/.gitignore','DeckEdge/.github/workflows/build.yml','DeckEdge/LICENSE','DeckEdge/packaging/build-release.ps1')){
                if($required -notin $entries){throw "Source manquante : $required"}
            }
            if($entries | Where-Object {$_ -match '\.(exe|dll|pdb|zip|png)$'}){throw 'Binaire ou capture présent dans les sources publiques.'}
        }else{
            foreach($required in @('DeckEdge/DeckEdge.exe','DeckEdge/portable.flag','DeckEdge/runtime/python.exe','DeckEdge/LibreHardwareMonitorLib.dll','DeckEdge/QRCoder.dll','DeckEdge/QRCoder-LICENSE.txt','DeckEdge/local_discovery.py','DeckEdge/prerequisites/PawnIO_setup.exe','DeckEdge/PYTHON-PACKAGES.json','DeckEdge/licenses/sources/SOURCES.json')){
                if($required -notin $entries){throw "Portable incomplet : $required"}
            }
        }
        foreach($entry in $archive.Entries){
            $path=$entry.FullName.Replace('\','/')
            if($path -match '^DeckEdge/(runtime|licenses)/'){continue}
            if($path -match '\.(py|js|css|html|md|ps1|cs|yml|json|txt|_pth)$'){
                $reader=New-Object IO.StreamReader($entry.Open())
                try{$content=$reader.ReadToEnd()}finally{$reader.Dispose()}
                if($content -match '(?i)C:\\Users\\[^\\]+\\'){throw "Chemin personnel dans $name : $path"}
            }
        }
    }finally{$archive.Dispose()}
}
foreach($line in Get-Content (Join-Path $DistributionDirectory 'SHA256SUMS.txt')){
    if($line -notmatch '^([a-f0-9]{64})  (.+)$'){throw 'Format SHA256SUMS incorrect.'}
    $expected=$Matches[1];$file=$Matches[2]
    if((Get-FileHash -LiteralPath (Join-Path $DistributionDirectory $file)).Hash.ToLowerInvariant() -ne $expected){throw "SHA256 incorrect : $file"}
}
Write-Output 'Archives vérifiées : fichiers requis, absence de données privées et empreintes SHA256.'
