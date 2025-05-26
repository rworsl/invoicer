#!/bin/bash
set -e

echo "🔄 Updating Invoice Generator..."

# Backup current version
echo "Creating backup..."
docker-compose exec backup /scripts/backup.sh

# Pull latest changes (if using git)
if [ -d ".git" ]; then
    echo "Pulling latest changes..."
    git pull origin main
fi

# Update Docker images
echo "Updating Docker images..."
docker-compose pull

# Rebuild and restart services
echo "Rebuilding services..."
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Wait for services
echo "Waiting for services to start..."
sleep 30

# Run any migrations or updates
echo "Running database migrations..."
docker-compose exec web python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database updated successfully')
"

echo "✅ Update completed successfully!"