param([string]$Destination = ".\backups")
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $Destination "tutor-$stamp"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
docker compose exec -T backend python -c "import sqlite3; src=sqlite3.connect('/app/data/tutor.db'); dst=sqlite3.connect('/app/data/backup.db'); src.backup(dst); dst.close(); src.close()"
docker compose cp backend:/app/data/backup.db (Join-Path $backupDir "tutor.db")
docker compose exec -T backend sh -c "test -f /app/data/config/ai.env"
if ($LASTEXITCODE -eq 0) {
    docker compose cp backend:/app/data/config/ai.env (Join-Path $backupDir "ai.env")
}
