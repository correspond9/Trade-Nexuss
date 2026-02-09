#!/bin/bash

# Quick Setup Script for VPS Deployment
set -e

echo "🚀 Broking Terminal V2 - Quick VPS Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please don't run this script as root. Run as regular user with sudo privileges."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_status "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    print_status "Docker installed. Please log out and log back in to use Docker without sudo."
    print_warning "After logging back in, run this script again."
    exit 0
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_status "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_status "Installing Git..."
    sudo apt update && sudo apt install -y git
fi

# Get repository URL
echo ""
read -p "Enter your Git repository URL: " REPO_URL

if [ -z "$REPO_URL" ]; then
    print_error "Repository URL is required."
    exit 1
fi

# Clone repository
print_status "Cloning repository..."
git clone "$REPO_URL" broking-terminal
cd broking-terminal/data_server_backend

# Setup environment file
if [ ! -f .env ]; then
    print_status "Setting up environment file..."
    cp .env.production .env
    
    echo ""
    print_warning "Please edit .env file with your configuration:"
    echo "  - POSTGRES_PASSWORD (database password)"
    echo "  - DHAN_CLIENT_ID, DHAN_API_KEY, DHAN_API_SECRET"
    echo "  - SECRET_KEY (run: openssl rand -hex 32)"
    echo "  - VITE_API_URL (your domain or IP)"
    echo ""
    read -p "Press Enter to continue after editing .env file..."
    
    # Check if .env has been modified
    if grep -q "your_.*_here" .env; then
        print_warning "Some values still contain placeholders. Please update .env file."
        read -p "Continue anyway? (y/N): " continue_anyway
        if [[ ! $continue_anyway =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    print_status ".env file already exists. Skipping environment setup."
fi

# Setup SSL
echo ""
read -p "Do you have a domain name? (y/N): " has_domain

if [[ $has_domain =~ ^[Yy]$ ]]; then
    read -p "Enter your domain name: " DOMAIN_NAME
    
    if [ ! -z "$DOMAIN_NAME" ]; then
        print_status "Setting up SSL for $DOMAIN_NAME..."
        
        # Install certbot
        sudo apt update && sudo apt install -y certbot
        
        # Generate certificate
        sudo certbot certonly --standalone -d "$DOMAIN_NAME"
        
        # Copy certificates
        mkdir -p ssl
        sudo cp "/etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem" ssl/cert.pem
        sudo cp "/etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem" ssl/key.pem
        sudo chown $USER:$USER ssl/*
        
        # Update VITE_API_URL in .env
        sed -i "s|https://your-domain.com/api|https://$DOMAIN_NAME/api|g" .env
        print_status "SSL certificate installed for $DOMAIN_NAME"
    fi
else
    print_status "Generating self-signed certificate..."
    mkdir -p ssl
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ssl/key.pem \
        -out ssl/cert.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    print_status "Self-signed certificate generated"
fi

# Create necessary directories
print_status "Creating directories..."
mkdir -p logs backups

# Setup firewall
print_status "Configuring firewall..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 22/tcp
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw --force enable
elif command -v firewall-cmd &> /dev/null; then
    sudo firewall-cmd --permanent --add-service=ssh
    sudo firewall-cmd --permanent --add-service=http
    sudo firewall-cmd --permanent --add-service=https
    sudo firewall-cmd --reload
else
    print_warning "Firewall not found. Please manually configure ports 22, 80, 443"
fi

# Deploy application
print_status "Deploying application..."
chmod +x scripts/deploy.sh
./scripts/deploy.sh

# Final instructions
echo ""
print_status "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Wait for containers to start (30-60 seconds)"
echo "2. Check status: docker-compose -f docker-compose.prod.yml ps"
echo "3. View logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "4. Test API: curl -k https://localhost/health"
echo ""
echo "Useful commands:"
echo "- Backup: ./scripts/backup.sh"
echo "- Restart: docker-compose -f docker-compose.prod.yml restart"
echo "- Stop: docker-compose -f docker-compose.prod.yml down"
echo "- Update: git pull && ./scripts/deploy.sh"
echo ""
echo "Documentation: VPS_DEPLOYMENT_GUIDE.md"
