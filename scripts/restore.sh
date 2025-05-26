# scripts/restore.sh - Database Restore Script
#!/bin/bash
set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file>"
    echo "Available backups:"
    ls -la /backups/backup_*.sql.gz
    exit 1
fi

BACKUP_FILE=$1
DB_HOST="db"
DB_NAME="invoice_db"
DB_USER="invoice_user"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "WARNING: This will overwrite the current database!"
echo "Backup file: $BACKUP_FILE"
echo "Database: $DB_NAME"
read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 1
fi

echo "Starting database restore..."

# Drop existing connections
PGPASSWORD=$POSTGRES_PASSWORD psql -h $DB_HOST -U $DB_USER -d postgres -c "
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = '$DB_NAME'
  AND pid <> pg_backend_pid();"

# Drop and recreate database
PGPASSWORD=$POSTGRES_PASSWORD dropdb -h $DB_HOST -U $DB_USER $DB_NAME
PGPASSWORD=$POSTGRES_PASSWORD createdb -h $DB_HOST -U $DB_USER $DB_NAME

# Restore from backup
zcat $BACKUP_FILE | PGPASSWORD=$POSTGRES_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME

echo "Database restored successfully from $BACKUP_FILE"
