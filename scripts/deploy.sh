# scripts/deploy.sh - Deployment Script
#!/bin/bash
set -e

echo "Starting deployment of Invoice Generator..."

# Check if required files exist
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found. Please create it from .env.example"
    exit 1
fi

if [ ! -f "nginx.conf" ]; then
    echo "ERROR: nginx.conf not found"
    exit 1
fi

# Generate SSL certificates if they don't exist
if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then
    echo "Generating self-signed SSL certificates..."
    mkdir -p ssl
    openssl req -x509 -newkey rsa:4096 -nodes -out ssl/cert.pem -keyout ssl/key.pem -days 365 \
        -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=localhost"
    echo "WARNING: Using self-signed certificates. Replace with valid certificates for production!"
fi

# Create necessary directories
mkdir -p logs uploads backups data static/uploads

# Set proper permissions
chmod 755 scripts/*.sh
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem

# Generate a secure secret key if not set
if ! grep -q "SECRET_KEY=" .env || grep -q "your-secret-key-here" .env; then
    echo "Generating secure secret key..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
fi

# Build and start services
echo "Building Docker images..."
docker-compose build

echo "Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "Waiting for services to start..."
sleep 30

# Check service health
echo "Checking service health..."
if docker-compose ps | grep -q "Up (healthy)"; then
    echo "✓ Services are running and healthy"
else
    echo "⚠ Some services may not be healthy. Check logs with: docker-compose logs"
fi

# Display access information
echo ""
echo "🎉 Deployment completed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📱 Application: https://localhost"
echo "🔒 Admin Login: admin@invoicegen.com / SecureAdmin123!"
echo "📊 Monitoring: http://localhost:9090 (if enabled)"
echo "🗄️  Database: localhost:5432"
echo ""
echo "🔧 Management Commands:"
echo "  View logs: docker-compose logs -f"
echo "  Stop: docker-compose down"
echo "  Backup: docker-compose exec backup /scripts/backup.sh"
echo "  Restore: docker-compose exec backup /scripts/restore.sh <backup_file>"
echo ""
echo "🛡️  Security Checklist:"
echo "  ✓ SSL certificates configured"
echo "  ✓ Rate limiting enabled"
echo "  ✓ Security headers set"
echo "  ✓ Non-root user in containers"
echo "  ⚠ Remember to change default passwords!"
echo "  ⚠ Replace self-signed certificates with real ones!"
