#!/bin/bash

echo "🔧 Running maintenance tasks..."

# Clean up old logs
echo "Cleaning up old logs..."
find logs/ -name "*.log" -mtime +7 -delete 2>/dev/null || true

# Clean up old uploads (if any cleanup logic needed)
echo "Cleaning up temporary files..."
find uploads/ -name "temp_*" -mtime +1 -delete 2>/dev/null || true

# Database maintenance
echo "Running database maintenance..."
docker-compose exec db psql -U invoice_user -d invoice_db -c "
VACUUM ANALYZE;
REINDEX DATABASE invoice_db;
"

# Redis maintenance
echo "Running Redis maintenance..."
docker-compose exec redis redis-cli BGREWRITEAOF

# Check disk space
echo "Checking disk space..."
df -h

# Check service health
echo "Checking service health..."
docker-compose ps

echo "✅ Maintenance completed!"