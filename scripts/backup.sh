# scripts/backup.sh - Database Backup Script
#!/bin/bash
set -e

# Configuration
BACKUP_DIR="/backups"
DB_HOST="db"
DB_NAME="invoice_db"
DB_USER="invoice_user"
BACKUP_RETENTION_DAYS=30
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql.gz"

echo "Starting database backup..."

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create backup
PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME | gzip > $BACKUP_FILE

# Verify backup was created
if [ -f "$BACKUP_FILE" ]; then
    echo "Backup created successfully: $BACKUP_FILE"
    echo "Backup size: $(du -h $BACKUP_FILE | cut -f1)"
else
    echo "ERROR: Backup failed!"
    exit 1
fi

# Clean up old backups
echo "Cleaning up backups older than $BACKUP_RETENTION_DAYS days..."
find $BACKUP_DIR -name "backup_*.sql.gz" -type f -mtime +$BACKUP_RETENTION_DAYS -delete

echo "Backup completed successfully"