param(
    [switch]$Zip,

    [ValidatePattern('^[a-zA-Z0-9][a-zA-Z0-9._-]*$')]
    [string]$Version = 'local'
)

$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $venvPython = '.\.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv.' }
    }

    & $venvPython -c "import sysconfig; raise SystemExit(sysconfig.get_platform() != 'win-amd64')"
    if ($LASTEXITCODE -ne 0) { throw 'The Windows x64 build requires x64 Python.' }

    & $venvPython -m pip install -r requirements.txt pyinstaller
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the build dependencies.' }

    $buildArgs = @(
        '--onedir'
        '--windowed'
        '--noconfirm'
        '--name', 'RenameFiles'
        '--specpath', 'build'
        '--collect-all', 'imageio_ffmpeg'
        'rename_files.py'
    )
    & $venvPython -m PyInstaller @buildArgs
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

    Write-Host 'Application: dist\RenameFiles\RenameFiles.exe'
    if ($Zip) {
        $archive = "dist\RenameFiles-$Version-windows-x64.zip"
        & $venvPython -m zipfile -c $archive 'dist\RenameFiles'
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the release archive.' }
        Write-Host "Archive: $archive"
    }
}
finally {
    Pop-Location
}
