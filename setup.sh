#!/bin/bash

# Automated Setup Script for Consignment Store ERPNext Development Environment
# This script automates the Docker-based development environment setup

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SITE_NAME="${SITE_NAME:-development.localhost}"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
COMPANY_NAME="${COMPANY_NAME:-Consignment Store Demo}"

# Helper functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    print_info "Docker and Docker Compose are installed"
}

create_env_file() {
    if [ ! -f .env ]; then
        print_info "Creating .env file from .env.example"
        cp .env.example .env
    else
        print_warn ".env file already exists, skipping creation"
    fi
}

build_containers() {
    print_info "Building Docker containers (this may take several minutes)..."
    docker-compose build --no-cache
}

start_containers() {
    print_info "Starting Docker containers..."
    docker-compose up -d mariadb redis-cache redis-queue

    print_info "Waiting for database to be ready..."
    sleep 10
}

setup_bench() {
    print_info "Setting up Frappe bench..."

    # Start backend container to run setup commands
    docker-compose up -d backend

    # Wait for backend to be ready
    sleep 5

    # Create new site
    print_info "Creating new site: ${SITE_NAME}..."
    docker-compose exec -T backend bench new-site ${SITE_NAME} \
        --mariadb-root-password ${DB_ROOT_PASSWORD} \
        --admin-password ${ADMIN_PASSWORD} \
        --no-mariadb-socket || print_warn "Site might already exist"

    # Install ERPNext
    print_info "Installing ERPNext (this may take a few minutes)..."
    docker-compose exec -T backend bench --site ${SITE_NAME} install-app erpnext || print_warn "ERPNext might already be installed"

    # Install Consignment Store
    print_info "Installing Consignment Store app..."
    docker-compose exec -T backend bench --site ${SITE_NAME} install-app consignment_store || print_warn "Consignment Store might already be installed"

    # Enable developer mode
    print_info "Enabling developer mode..."
    docker-compose exec -T backend bench --site ${SITE_NAME} set-config developer_mode 1

    # Clear cache
    print_info "Clearing cache..."
    docker-compose exec -T backend bench --site ${SITE_NAME} clear-cache

    # Migrate
    print_info "Running migrations..."
    docker-compose exec -T backend bench --site ${SITE_NAME} migrate
}

start_services() {
    print_info "Starting all services..."
    docker-compose up -d

    print_info "Waiting for services to start..."
    sleep 10
}

print_success() {
    echo ""
    echo "=========================================="
    print_info "Setup completed successfully!"
    echo "=========================================="
    echo ""
    echo "Access your ERPNext instance at: http://localhost:8000"
    echo "Site Name: ${SITE_NAME}"
    echo "Username: Administrator"
    echo "Password: ${ADMIN_PASSWORD}"
    echo ""
    echo "Useful commands:"
    echo "  - View logs: docker-compose logs -f"
    echo "  - Stop services: docker-compose down"
    echo "  - Restart services: docker-compose restart"
    echo "  - Access bench: docker-compose exec backend bash"
    echo "  - Access shell: docker-compose exec backend bench --site ${SITE_NAME} console"
    echo ""
}

# Main execution
main() {
    print_info "Starting Consignment Store Development Environment Setup"

    check_docker
    create_env_file
    build_containers
    start_containers
    setup_bench
    start_services
    print_success
}

# Run main function
main
