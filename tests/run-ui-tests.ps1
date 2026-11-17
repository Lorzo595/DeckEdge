param([int]$Port = 5011, [string]$DataDirectory = '.build/ui-test-data')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
. (Join-Path $PSScriptRoot 'test-output-path.ps1')

$data = Resolve-TestOutputPath -Root $root -Path $DataDirectory
Remove-Item -LiteralPath $data -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $data -Force | Out-Null

$venvPython = Join-Path $root '.venv/Scripts/python.exe'
$python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { 'python' }

$env:DECKEDGE_DATA_DIR = $data
$env:DECKEDGE_PORT = "$Port"
$stdout = Join-Path $data 'server.out.log'
$stderr = Join-Path $data 'server.err.log'
$server = Start-Process -FilePath $python `
    -ArgumentList @('-m', 'uvicorn', 'server:app', '--host', '127.0.0.1', '--port', "$Port") `
    -PassThru -NoNewWindow -RedirectStandardOutput $stdout -RedirectStandardError $stderr

try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 80; $attempt++) {
        if ($server.HasExited) {
            throw "Le serveur de test s'est arrêté. Voir $stderr"
        }
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 1
            if ($response.StatusCode -eq 200) { $ready = $true; break }
        } catch { }
        Start-Sleep -Milliseconds 250
    }
    if (-not $ready) { throw "Le serveur de test ne répond pas sur le port $Port. Voir $stderr" }

    $env:DECKEDGE_TEST_URL = "http://127.0.0.1:$Port"
    $tests = @(
        'tests/studio-shell.cjs',
        'tests/studio-layout.cjs',
        'tests/media-library.cjs',
        'tests/studio-ergonomics.cjs',
        'tests/studio-colors.cjs',
        'tests/mobile-preview.cjs',
        'tests/mobile-gestures.cjs',
        'tests/startup-profile.cjs',
        'tests/diagnostics.cjs',
        'tests/profiles.cjs',
        'tests/sequences.cjs',
        'tests/studio-actions.cjs',
        'tests/mobile-accessibility.cjs',
        'tests/folders.cjs',
        'tests/phones.cjs',
        'tests/i18n.cjs',
        'tests/studio-i18n.cjs'
    )
    foreach ($test in $tests) {
        node $test
        if ($LASTEXITCODE -ne 0) { throw "Test navigateur en échec : $test" }
    }
} finally {
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    }
}
