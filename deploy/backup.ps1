param([string]$Destination = ".\backups")
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
docker compose exec -T backend python -c "import sqlite3; src=sqlite3.connect('/app/data/tutor.db'); dst=sqlite3.connect('/app/data/backup.db'); src.backup(dst); dst.close(); src.close()"
docker compose cp backend:/app/data/backup.db (Join-Path $Destination "tutor-$stamp.db")

