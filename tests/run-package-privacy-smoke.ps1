$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'test-output-path.ps1')
$output=Resolve-TestOutputPath -Root $root -Path '.build/package-privacy-smoke'
New-Item -ItemType Directory -Path $output -Force | Out-Null
$version=(Get-Content (Join-Path $root 'VERSION') -Raw).Trim()
Add-Type -AssemblyName System.IO.Compression,System.IO.Compression.FileSystem
foreach($entry in @('DeckEdge/.phones.json','DeckEdge/.phones.json.123.tmp','DeckEdge/.PHONES.JSON','DeckEdge/backups/.phones.json')){
    $folder=Join-Path $output ([Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
    $zip=[IO.Compression.ZipFile]::Open((Join-Path $folder "DeckEdge-$version-Portable-x64.zip"),[IO.Compression.ZipArchiveMode]::Create)
    try {
        $writer=[IO.StreamWriter]::new($zip.CreateEntry($entry).Open())
        try {$writer.Write('{"phones":[]}')} finally {$writer.Dispose()}
    } finally {$zip.Dispose()}
    $rejected=$false
    try {& (Join-Path $root 'packaging/check-release.ps1') -DistributionDirectory $folder}
    catch {
        if($_.Exception.Message -notlike '*Fichier privé ou temporaire*' -or $_.Exception.Message -notlike '*phones.json*'){throw}
        $rejected=$true
    }
    if(-not $rejected){throw "Private pairing registry accepted: $entry"}
}
Write-Output 'OK: private phone registries, temporary copies and case variants rejected from distributions.'
