# scripts/security-check.sh - Security Audit Script
#!/bin/bash

echo "🔐 Invoice Generator Security Audit"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ CRITICAL: Do not run this application as root!"
else
    echo "✓ Not running as root"
fi

# Check environment file
if [ -f ".env" ]; then
    echo "✓ Environment file exists"
    
    # Check for default secret key
    if grep -q "your-secret-key-here" .env; then
        echo "❌ CRITICAL: Default secret key detected! Change SECRET_KEY in .env"
    else
        echo "✓ Custom secret key configured"
    fi
    
    # Check for production environment
    if grep -q "FLASK_ENV=production" .env; then
        echo "✓ Production environment configured"
    else
        echo "⚠ WARNING: Not running in production mode"
    fi
    
    # Check for secure cookies
    if grep -q "SESSION_COOKIE_SECURE=True" .env; then
        echo "✓ Secure cookies enabled"
    else
        echo "⚠ WARNING: Secure cookies not enabled"
    fi
else
    echo "❌ CRITICAL: .env file not found!"
fi

# Check SSL certificates
if [ -f "ssl/cert.pem" ] && [ -f "ssl/key.pem" ]; then
    echo "✓ SSL certificates present"
    
    # Check if self-signed
    if openssl x509 -in ssl/cert.pem -text -noout | grep -q "Issuer.*Subject"; then
        echo "⚠ WARNING: Self-signed certificate detected"
    else
        echo "✓ Valid SSL certificate"
    fi
else
    echo "❌ CRITICAL: SSL certificates not found!"
fi

# Check file permissions
echo ""
echo "📁 File Permissions:"
for file in "ssl/key.pem" ".env" "scripts/*.sh"; do
    if [ -f "$file" ]; then
        perms=$(stat -c %a "$file" 2>/dev/null || stat -f %A "$file" 2>/dev/null)
        echo "  $file: $perms"
    fi
done

# Check Docker security
echo ""
echo "🐳 Docker Security:"
if docker-compose ps | grep -q "Up"; then
    echo "✓ Services are running"
    
    # Check if containers are running as root
    for container in $(docker-compose ps -q); do
        user=$(docker exec $container whoami 2>/dev/null || echo "unknown")
        name=$(docker inspect --format '{{.Name}}' $container | sed 's/\///')
        if [ "$user" = "root" ]; then
            echo "⚠ WARNING: Container $name running as root"
        else
            echo "✓ Container $name running as: $user"
        fi
    done
else
    echo "❌ Services not running"
fi

# Check network security
echo ""
echo "🌐 Network Security:"
if command -v nmap &> /dev/null; then
    open_ports=$(nmap -sT localhost 2>/dev/null | grep "open" | wc -l)
    echo "  Open ports on localhost: $open_ports"
else
    echo "  nmap not available for port scanning"
fi

# Check log files
echo ""
echo "📋 Log Analysis:"
if [ -d "logs" ]; then
    echo "✓ Logs directory exists"
    log_files=$(find logs -name "*.log" | wc -l)
    echo "  Log files: $log_files"
else
    echo "⚠ WARNING: Logs directory not found"
fi

echo ""
echo "🔍 Security Recommendations:"
echo "  1. Use strong, unique passwords for all accounts"
echo "  2. Enable two-factor authentication if available"
echo "  3. Regularly update dependencies and Docker images"
echo "  4. Monitor logs for suspicious activities"
echo "  5. Use a Web Application Firewall (WAF) in production"
echo "  6. Implement regular backups and test restore procedures"
echo "  7. Use a reverse proxy with rate limiting"
echo "  8. Keep the system updated with security patches"