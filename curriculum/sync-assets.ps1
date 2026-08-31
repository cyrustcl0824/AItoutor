param(
    [string]$Release = "v1.1.0-assets",
    [string]$Destination = "$PSScriptRoot\assets"
)
$ErrorActionPreference = "Stop"
$repo = "wuwangzhang1216/ChinaTextbookStudyFree"
New-Item -ItemType Directory -Force -Path $Destination | Out-Null

foreach ($asset in @("textbook-pages.zip", "data-source.zip", "data.zip")) {
    $archive = Join-Path $Destination $asset
    if (-not (Test-Path -LiteralPath $archive)) {
        Invoke-WebRequest -Uri "https://github.com/$repo/releases/download/$Release/$asset" -OutFile $archive
    }
    $folder = Join-Path $Destination ([IO.Path]::GetFileNameWithoutExtension($asset))
    if (-not (Test-Path -LiteralPath $folder)) {
        Expand-Archive -LiteralPath $archive -DestinationPath $folder
    }
}

Write-Host "Assets ready at $Destination"

