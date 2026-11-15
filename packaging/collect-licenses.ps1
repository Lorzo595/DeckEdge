param([Parameter(Mandatory=$true)][string]$Destination)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$cache=Join-Path $root '.build/cache'
New-Item -ItemType Directory -Path $Destination -Force | Out-Null
$sources=Join-Path $Destination 'sources'; New-Item -ItemType Directory -Path $sources -Force | Out-Null
$sourceRepos=@(
    @{Name='LibreHardwareMonitor'; Repo='LibreHardwareMonitor/LibreHardwareMonitor'; Commit='3d331e3370efb858411f19511373eff65a218701'},
    @{Name='PawnIO.Modules'; Repo='namazso/PawnIO.Modules'; Commit='4aa792beb020a14c8261072e9786d2dfb38489d9'},
    @{Name='PawnIO'; Repo='namazso/PawnIO'; Commit='e1043d7750f501b6b0d3ac0a71bd5b9406cd17b6'}
)
$sourceManifest=@()
foreach($source in $sourceRepos) {
    $path=Join-Path $cache ($source.Name+'-source.zip')
    $url='https://codeload.github.com/'+$source.Repo+'/zip/'+$source.Commit
    if(-not(Test-Path -LiteralPath $path)){Invoke-WebRequest -Uri $url -OutFile $path -UseBasicParsing}
    Copy-Item -LiteralPath $path -Destination $sources
    $sourceManifest+=@{name=$source.Name;commit=$source.Commit;url=$url;sha256=(Get-FileHash $path).Hash.ToLowerInvariant()}
}
$zeroconf=Invoke-RestMethod 'https://pypi.org/pypi/zeroconf/0.154.0/json'
$sdist=$zeroconf.urls | Where-Object {$_.packagetype -eq 'sdist'} | Select-Object -First 1
if(-not $sdist){throw 'Sources zeroconf introuvables.'}
$zeroconfArchive=Join-Path $cache $sdist.filename
if(-not(Test-Path $zeroconfArchive)){Invoke-WebRequest -Uri $sdist.url -OutFile $zeroconfArchive -UseBasicParsing}
if((Get-FileHash $zeroconfArchive).Hash.ToLowerInvariant() -ne $sdist.digests.sha256){throw 'SHA256 des sources zeroconf incorrect.'}
Copy-Item -LiteralPath $zeroconfArchive -Destination $sources
$sourceManifest+=@{name='zeroconf';version='0.154.0';url=$sdist.url;sha256=$sdist.digests.sha256}
$sourceManifest | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 (Join-Path $sources 'SOURCES.json')
@'
Original, unmodified sources. Extract each archive to read the licenses
and rebuild instructions for its project.
LibreHardwareMonitor 0.9.6: dotnet build LibreHardwareMonitorLib -c Release -f net472.
PawnIO.Modules 0.1.6: instructions and Pawn compiler in the project README.
PawnIO 2.1.0: driver build instructions in the project README.
zeroconf 0.154.0: Python/Cython sources, license and project instructions in
the provided PyPI source package; rebuild with the tools declared in pyproject.toml.
.NET libraries and Python modules remain replaceable with compatible versions;
DeckEdge does not restrict their modification.
SOURCES.json lists the commits and archive hashes provided.
'@ | Set-Content -Encoding utf8 (Join-Path $sources 'README.txt')
$notice=Join-Path $cache 'LHM-THIRD-PARTY-NOTICES.txt'
if(-not(Test-Path $notice)){Invoke-WebRequest 'https://raw.githubusercontent.com/LibreHardwareMonitor/LibreHardwareMonitor/3d331e3370efb858411f19511373eff65a218701/THIRD-PARTY-NOTICES.txt' -OutFile $notice -UseBasicParsing}
Copy-Item $notice -Destination $Destination
Copy-Item (Join-Path $root 'desktop/LibreHardwareMonitor-LICENSE.txt') -Destination $Destination
$inventory=@()
foreach($dll in Get-ChildItem (Join-Path $root '.build/lhm') -Filter '*.dll') {
    if($dll.Name -in @('Aga.Controls.dll','OxyPlot.dll','OxyPlot.WindowsForms.dll','LibreHardwareMonitorLib.dll')){continue}
    $name=[IO.Path]::GetFileNameWithoutExtension($dll.Name)
    $version=($dll.VersionInfo.ProductVersion -split '\+')[0]
    if($name -eq 'Microsoft.Win32.TaskScheduler'){$name='TaskScheduler';$version='2.12.2'}
    $id=$name.ToLowerInvariant()
    $archive=Join-Path $cache ("nuget-$id-$version.zip")
    $url="https://api.nuget.org/v3-flatcontainer/$id/$version/$id.$version.nupkg"
    if(-not(Test-Path $archive)){Invoke-WebRequest -Uri $url -OutFile $archive -UseBasicParsing}
    $expanded=Join-Path $cache ("nuget-$id-$version")
    if(-not(Test-Path $expanded)){Expand-Archive -LiteralPath $archive -DestinationPath $expanded}
    $target=Join-Path $Destination ("dotnet/$name-$version");New-Item -ItemType Directory -Path $target -Force | Out-Null
    $nuspec=Get-ChildItem $expanded -Filter '*.nuspec' | Select-Object -First 1
    Copy-Item $nuspec.FullName -Destination $target
    [xml]$spec=Get-Content $nuspec.FullName -Raw
    $license=$spec.package.metadata.license
    foreach($file in Get-ChildItem $expanded -Recurse -File | Where-Object {$_.Name -match '(?i)license|licence|copyright|notice'}) {
        $relative=$file.FullName.Substring($expanded.Length+1);$licenseTarget=Join-Path $target $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $licenseTarget) -Force | Out-Null
        Copy-Item $file.FullName -Destination $licenseTarget
    }
    if($license.type -eq 'expression') {
        Invoke-WebRequest -Uri ('https://licenses.nuget.org/'+[Uri]::EscapeDataString($license.InnerText)) -OutFile (Join-Path $target 'LICENSE.txt') -UseBasicParsing
    }
    $inventory+=@{file=$dll.Name;package=$name;version=$version;url=$url;sha256=(Get-FileHash $archive).Hash.ToLowerInvariant()}
}
$inventory | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 (Join-Path $Destination 'DOTNET-PACKAGES.json')
