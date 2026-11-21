param([string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot))

$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath $ProjectRoot).Path
$pythonw = Join-Path $project '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw -PathType Leaf)) {
    throw 'Ambiente Python do projeto nao encontrado.'
}
if (-not (Test-Path -LiteralPath (Join-Path $project 'app.py') -PathType Leaf)) {
    throw 'Aplicativo nao encontrado nesta pasta.'
}

$desktop = [Environment]::GetFolderPath('Desktop')
$programs = Join-Path ([Environment]::GetFolderPath('Programs')) 'Osler'
$startup = [Environment]::GetFolderPath('Startup')
$items = @(
    @{ Path = (Join-Path $desktop 'Osler.lnk'); Arguments = '-m osler.local_launcher' },
    @{ Path = (Join-Path $programs 'Osler.lnk'); Arguments = '-m osler.local_launcher' },
    @{ Path = (Join-Path $programs 'Encerrar Osler.lnk'); Arguments = '-m osler.local_launcher --stop' },
    @{ Path = (Join-Path $startup 'Osler.lnk'); Arguments = '-m osler.local_launcher --background' }
)
$shell = New-Object -ComObject WScript.Shell
# Conferir todos os destinos antes de escrever, preservando atalhos de outros apps.
foreach ($item in $items) {
    if (Test-Path -LiteralPath $item.Path) {
        $existing = $shell.CreateShortcut($item.Path)
        if ($existing.TargetPath -ne $pythonw -or $existing.WorkingDirectory -ne $project -or $existing.Arguments -ne $item.Arguments) {
            throw "Ja existe um atalho diferente neste destino: $($item.Path)"
        }
    }
}
if (-not (Test-Path -LiteralPath $programs)) {
    New-Item -ItemType Directory -Path $programs | Out-Null
}
foreach ($item in $items) {
    $link = $shell.CreateShortcut($item.Path)
    $link.TargetPath = $pythonw
    $link.Arguments = $item.Arguments
    $link.WorkingDirectory = $project
    $link.Description = 'Osler - estudo local'
    $link.WindowStyle = 7
    $link.IconLocation = "$pythonw,0"
    $link.Save()
}
$items | ConvertTo-Json
