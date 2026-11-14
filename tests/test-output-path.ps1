function Resolve-TestOutputPath {
    param([string]$Root, [string]$Path)

    $rootFull = [IO.Path]::GetFullPath($Root)
    $allowedRoot = [IO.Path]::GetFullPath((Join-Path $rootFull '.build'))
    $target = if ([IO.Path]::IsPathRooted($Path)) {
        [IO.Path]::GetFullPath($Path)
    } else {
        [IO.Path]::GetFullPath((Join-Path $rootFull $Path))
    }

    $prefix = $allowedRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (-not $target.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Le dossier de test doit être sous $allowedRoot (reçu : $target)."
    }
    return $target
}
