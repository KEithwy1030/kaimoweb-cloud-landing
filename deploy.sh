#!/bin/bash

################################################################################
# VPN Distribution System - Deployment Script
# This script automates the deployment process on Linux servers
################################################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="vpn-distribution"
INSTALL_DIR="/opt/${PROJECT_NAME}"
SERVICE_NAME="vpn-distribution"
PYTHON_VERSION="3.9"
APP_PORT=8000

# Default admin credentials (will be created during initialization)
DEFAULT_ADMIN_EMAIL="admin@vpn-local.com"
DEFAULT_ADMIN_PASSWORD="admin123456"

################################################################################
# Helper Functions
################################################################################

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 is not installed"
        return 1
    fi
    return 0
}

################################################################################
# Pre-flight Checks
################################################################################

preflight_checks() {
    print_info "Running pre-flight checks..."

    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        print_warning "Running as root. Script will create service for current user after setup."
    fi

    # Check Python version
    if check_command python3; then
        PYTHON_VERSION_FULL=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        print_info "Python version: $PYTHON_VERSION_FULL"
    else
        print_error "Python 3 is not installed. Please install Python 3.9+ first."
        exit 1
    fi

    # Check pip
    if ! check_command pip3; then
        print_error "pip3 is not installed"
        exit 1
    fi

    # Check git (optional)
    if check_command git; then
        print_info "Git is installed"
    else
        print_warning "Git is not installed (optional)"
    fi

    print_info "Pre-flight checks completed!"
}

################################################################################
# Installation Functions
################################################################################

install_dependencies() {
    print_info "Installing Python dependencies..."

    cd "$INSTALL_DIR"

    # Upgrade pip
    pip3 install --upgrade pip

    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
        print_info "Dependencies installed successfully!"
    else
        print_error "requirements.txt not found!"
        exit 1
    fi
}

initialize_database() {
    print_info "Initializing database..."

    cd "$INSTALL_DIR"

    # Run database initialization
    if [ -f "init_db.py" ]; then
        python3 init_db.py
        print_info "Database initialized successfully!"
    else
        print_error "init_db.py not found!"
        exit 1
    fi
}

create_directories() {
    print_info "Creating project directories..."

    # Create installation directory
    if [ ! -d "$INSTALL_DIR" ]; then
        sudo mkdir -p "$INSTALL_DIR"
        sudo chown $USER:$USER "$INSTALL_DIR"
        print_info "Created directory: $INSTALL_DIR"
    else
        print_info "Directory already exists: $INSTALL_DIR"
    fi

    # Create necessary subdirectories
    mkdir -p "$INSTALL_DIR/logs"
    mkdir -p "$INSTALL_DIR/backups"

    print_info "Directories created!"
}

setup_systemd_service() {
    print_info "Setting up systemd service..."

    # Get current username
    CURRENT_USER=$(whoami)

    # Create systemd service file
    sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=VPN Distribution System
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${INSTALL_DIR}
Environment="PATH=${INSTALL_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT}
Restart=always
RestartSec=10
StandardOutput=append:${INSTALL_DIR/logs/app.log
StandardError=append:${INSTALL_DIR/logs/error.log}

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    sudo systemctl daemon-reload

    print_info "Systemd service created!"
}

create_nginx_config() {
    print_info "Creating Nginx configuration (optional)..."

    # Ask for domain
    read -p "Enter your domain name (leave empty to skip Nginx setup): " DOMAIN_NAME

    if [ -z "$DOMAIN_NAME" ]; then
        print_warning "Skipping Nginx configuration"
        return
    fi

    # Check if Nginx is installed
    if ! check_command nginx; then
        print_warning "Nginx is not installed. Skipping Nginx configuration."
        return
    fi

    # Create Nginx config
    sudo tee /etc/nginx/sites-available/${SERVICE_NAME} > /dev/null <<EOF
server {
    listen 80;
    server_name ${DOMAIN_NAME};

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Increase client body size for file uploads
    client_max_body_size 10M;
}
EOF

    # Enable site
    sudo ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/

    # Test Nginx config
    sudo nginx -t

    print_info "Nginx configuration created for ${DOMAIN_NAME}"
    print_info "Run 'sudo systemctl reload nginx' to apply Nginx configuration"
}

################################################################################
# Service Management Functions
################################################################################

start_service() {
    print_info "Starting ${SERVICE_NAME} service..."

    sudo systemctl enable ${SERVICE_NAME}
    sudo systemctl start ${SERVICE_NAME}

    # Wait a moment for service to start
    sleep 2

    # Check service status
    if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
        print_info "Service started successfully!"
        sudo systemctl status ${SERVICE_NAME} --no-pager
    else
        print_error "Service failed to start!"
        print_info "Check logs with: journalctl -u ${SERVICE_NAME} -f"
        exit 1
    fi
}

stop_service() {
    print_info "Stopping ${SERVICE_NAME} service..."
    sudo systemctl stop ${SERVICE_NAME}
    print_info "Service stopped!"
}

restart_service() {
    print_info "Restarting ${SERVICE_NAME} service..."
    sudo systemctl restart ${SERVICE_NAME}
    print_info "Service restarted!"
}

show_status() {
    print_info "Service status:"
    sudo systemctl status ${SERVICE_NAME} --no-pager
}

show_logs() {
    print_info "Showing logs (Ctrl+C to exit):"
    sudo journalctl -u ${SERVICE_NAME} -f
}

################################################################################
# Maintenance Functions
################################################################################

backup_database() {
    print_info "Backing up database..."

    BACKUP_DIR="${INSTALL_DIR}/backups"
    BACKUP_FILE="vpn_distribution_$(date +%Y%m%d_%H%M%S).db"

    if [ -f "${INSTALL_DIR}/vpn_distribution.db" ]; then
        cp "${INSTALL_DIR}/vpn_distribution.db" "${BACKUP_DIR}/${BACKUP_FILE}"
        print_info "Database backed up to: ${BACKUP_DIR}/${BACKUP_FILE}"
    else
        print_warning "Database file not found!"
    fi
}

update_application() {
    print_info "Updating application..."

    # Stop service
    stop_service

    # Backup database
    backup_database

    # Pull latest code (if using git)
    if [ -d "${INSTALL_DIR}/.git" ]; then
        cd "$INSTALL_DIR"
        git pull
        print_info "Code updated from git repository"
    else
        print_warning "Not a git repository. Please update manually."
    fi

    # Install/update dependencies
    install_dependencies

    # Restart service
    start_service

    print_info "Application updated!"
}

################################################################################
# Uninstall Function
################################################################################

uninstall() {
    print_warning "Uninstalling VPN Distribution System..."

    read -p "Are you sure you want to uninstall? (y/N): " CONFIRM
    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        print_info "Uninstall cancelled"
        return
    fi

    # Stop and disable service
    sudo systemctl stop ${SERVICE_NAME} 2>/dev/null || true
    sudo systemctl disable ${SERVICE_NAME} 2>/dev/null || true

    # Remove service file
    sudo rm -f /etc/systemd/system/${SERVICE_NAME}.service
    sudo systemctl daemon-reload

    # Ask about data removal
    read -p "Remove all data including database? (y/N): " REMOVE_DATA
    if [ "$REMOVE_DATA" = "y" ] || [ "$REMOVE_DATA" = "Y" ]; then
        sudo rm -rf "$INSTALL_DIR"
        print_info "All data removed"
    else
        print_info "Data kept in: $INSTALL_DIR"
    fi

    # Remove Nginx config (if exists)
    sudo rm -f /etc/nginx/sites-available/${SERVICE_NAME}
    sudo rm -f /etc/nginx/sites-enabled/${SERVICE_NAME}

    print_info "Uninstall completed!"
}

################################################################################
# Installation Menu
################################################################################

show_menu() {
    echo ""
    echo "=========================================="
    echo "  VPN Distribution System - Deployment"
    echo "=========================================="
    echo ""
    echo "  1. Full Installation"
    echo "  2. Start Service"
    echo "  3. Stop Service"
    echo "  4. Restart Service"
    echo "  5. Show Status"
    echo "  6. Show Logs"
    echo "  7. Backup Database"
    echo "  8. Update Application"
    echo "  9. Uninstall"
    echo "  0. Exit"
    echo ""
    echo "=========================================="
}

################################################################################
# Main Installation Process
################################################################################

full_installation() {
    print_info "Starting full installation..."

    # Run pre-flight checks
    preflight_checks

    # Create directories
    create_directories

    # Check if files exist in current directory
    if [ -f "requirements.txt" ] && [ -f "init_db.py" ]; then
        print_info "Copying project files to ${INSTALL_DIR}..."
        cp -r . "$INSTALL_DIR/"
    else
        print_warning "Project files not found in current directory"
        read -p "Enter path to project files: " PROJECT_PATH
        if [ -d "$PROJECT_PATH" ]; then
            cp -r "$PROJECT_PATH"/* "$INSTALL_DIR/"
        else
            print_error "Invalid path!"
            exit 1
        fi
    fi

    # Install dependencies
    install_dependencies

    # Initialize database
    initialize_database

    # Setup systemd service
    setup_systemd_service

    # Optionally setup Nginx
    create_nginx_config

    # Start service
    start_service

    # Show completion message
    echo ""
    echo "=========================================="
    print_info "Installation completed successfully!"
    echo "=========================================="
    echo ""
    echo "Access Information:"
    echo "  API Endpoint: http://localhost:${APP_PORT}"
    echo "  API Docs: http://localhost:${APP_PORT}/docs"
    echo "  Default Admin: ${DEFAULT_ADMIN_EMAIL}"
    echo "  Default Password: ${DEFAULT_ADMIN_PASSWORD}"
    echo ""
    print_warning "Please change the default admin password!"
    echo ""
    echo "Useful Commands:"
    echo "  Start: sudo systemctl start ${SERVICE_NAME}"
    echo "  Stop: sudo systemctl stop ${SERVICE_NAME}"
    echo "  Restart: sudo systemctl restart ${SERVICE_NAME}"
    echo "  Status: sudo systemctl status ${SERVICE_NAME}"
    echo "  Logs: sudo journalctl -u ${SERVICE_NAME} -f"
    echo ""
}

################################################################################
# Main Script
################################################################################

# If script is run with arguments
if [ $# -gt 0 ]; then
    case $1 in
        install)
            full_installation
            ;;
        start)
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        backup)
            backup_database
            ;;
        update)
            update_application
            ;;
        uninstall)
            uninstall
            ;;
        *)
            echo "Usage: $0 {install|start|stop|restart|status|logs|backup|update|uninstall}"
            exit 1
            ;;
    esac
    exit 0
fi

# Interactive menu
while true; do
    show_menu
    read -p "Enter your choice [0-9]: " choice

    case $choice in
        1)
            full_installation
            ;;
        2)
            start_service
            ;;
        3)
            stop_service
            ;;
        4)
            restart_service
            ;;
        5)
            show_status
            ;;
        6)
            show_logs
            ;;
        7)
            backup_database
            ;;
        8)
            update_application
            ;;
        9)
            uninstall
            ;;
        0)
            print_info "Exiting..."
            exit 0
            ;;
        *)
            print_error "Invalid choice!"
            ;;
    esac

    read -p "Press Enter to continue..."
done
