# Docker Setup Guide for Consignment Store

This guide provides detailed information about the Docker setup for the ERPNext Consignment Store development environment.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## Overview

The Docker setup provides a complete, isolated development environment for the Consignment Store ERPNext app. It includes:

- ERPNext v15 with all dependencies
- MariaDB database
- Redis for caching and queuing
- Nginx web server
- WebSocket server for real-time updates
- Background job workers and scheduler

## Prerequisites

### System Requirements

- **OS:** Linux, macOS, or Windows with WSL2
- **RAM:** Minimum 4GB, recommended 8GB
- **Disk:** At least 10GB free space
- **Docker:** Version 20.10 or higher
- **Docker Compose:** Version 2.0 or higher

### Installation

**Docker on Linux:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**Docker on macOS:**
Download and install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop)

**Docker on Windows:**
Download and install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)

## Quick Start

```bash
# 1. Clone the repository
git clone <repository-url>
cd erpnext_consignment_store

# 2. Copy environment file
cp .env.example .env

# 3. Run setup script
./setup.sh
```

The setup script will:
1. Build Docker images
2. Start database and cache services
3. Create a new Frappe site
4. Install ERPNext
5. Install Consignment Store app
6. Configure the site
7. Start all services

This process takes 10-15 minutes on the first run.

## Architecture

### Services

The Docker Compose setup includes these services:

#### Core Services

**mariadb**
- Purpose: Database server
- Image: `mariadb:10.6`
- Port: 3306 (internal)
- Volume: `mariadb-data`

**redis-cache**
- Purpose: Cache storage
- Image: `redis:7-alpine`
- Port: 6379 (internal)
- Volume: `redis-cache-data`

**redis-queue**
- Purpose: Background job queue
- Image: `redis:7-alpine`
- Port: 6379 (internal)
- Volume: `redis-queue-data`

#### Application Services

**backend**
- Purpose: Main Frappe application server
- Build: Custom Dockerfile
- Port: 8000 (internal)
- Volumes: App code, sites, logs
- Command: `bench start`

**frontend**
- Purpose: Nginx reverse proxy
- Image: `frappe/erpnext:v15`
- Port: 8000 (exposed)
- Serves static files and proxies to backend

**websocket**
- Purpose: Real-time updates via Socket.IO
- Build: Custom Dockerfile
- Port: 9000 (internal)
- Command: `node socketio.js`

#### Background Services

**scheduler**
- Purpose: Runs scheduled tasks
- Build: Custom Dockerfile
- Command: `bench schedule`

**worker-short**
- Purpose: Handles quick background jobs
- Build: Custom Dockerfile
- Command: `bench worker --queue short`

**worker-long**
- Purpose: Handles long-running background jobs
- Build: Custom Dockerfile
- Command: `bench worker --queue long`

### Volumes

- `mariadb-data` - Database files
- `redis-cache-data` - Cache data
- `redis-queue-data` - Queue data
- `sites-data` - Frappe sites and configuration
- `logs-data` - Application logs

### Network

All services communicate via the `frappe-network` bridge network.

## Configuration

### Environment Variables

Edit `.env` file to customize:

```bash
# Site Configuration
SITE_NAME=development.localhost
HTTP_PORT=8000

# Database
DB_ROOT_PASSWORD=admin

# Admin User
ADMIN_PASSWORD=admin

# Frappe/ERPNext Versions
FRAPPE_BRANCH=version-15
ERPNEXT_BRANCH=version-15
```

### Custom Configuration

To change Frappe site configuration:

```bash
# Access the backend container
docker-compose exec backend bash

# Use bench commands
bench --site development.localhost set-config [key] [value]
```

## Common Tasks

### Starting and Stopping

```bash
# Start all services
make start
# or
docker-compose up -d

# Stop all services
make stop
# or
docker-compose down

# Restart services
make restart
# or
docker-compose restart
```

### Viewing Logs

```bash
# All services
make logs

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Accessing the Container

```bash
# Bash shell
make bash
# or
docker-compose exec backend bash

# Frappe console
make console
# or
docker-compose exec backend bench --site development.localhost console
```

### Database Operations

```bash
# Run migrations
make migrate

# Backup site
docker-compose exec backend bench --site development.localhost backup

# Restore backup
docker-compose exec backend bench --site development.localhost restore [backup-file]

# Access MariaDB
docker-compose exec mariadb mysql -u root -padmin
```

### App Development

```bash
# Clear cache
make clear-cache

# Rebuild app after changes
make rebuild

# Run tests
docker-compose exec backend bench --site development.localhost run-tests --app consignment_store

# Install new dependency
docker-compose exec backend bash
cd apps/consignment_store
pip install [package-name]
```

## Troubleshooting

### Services Won't Start

**Problem:** Container exits immediately

**Solution:**
```bash
# Check logs
docker-compose logs [service-name]

# Check container status
docker-compose ps

# Try rebuilding
docker-compose build --no-cache [service-name]
```

### Database Connection Errors

**Problem:** Can't connect to database

**Solution:**
```bash
# Check if MariaDB is running
docker-compose ps mariadb

# Check MariaDB logs
docker-compose logs mariadb

# Restart MariaDB
docker-compose restart mariadb

# Wait for health check
docker-compose ps
```

### Port Already in Use

**Problem:** Port 8000 is already in use

**Solution:**
```bash
# Edit .env file
HTTP_PORT=8080

# Restart services
docker-compose down
docker-compose up -d
```

### Out of Memory

**Problem:** Container is killed due to OOM

**Solution:**
```bash
# Increase Docker memory limit in Docker Desktop settings
# Or free up memory
docker system prune -a

# Reduce workers
# Comment out worker-long in docker-compose.yml
```

### Permission Issues

**Problem:** Permission denied errors

**Solution:**
```bash
# Fix volume permissions
docker-compose exec backend bash
chown -R frappe:frappe /home/frappe/frappe-bench/sites

# Or reset volumes
docker-compose down -v
./setup.sh
```

## Advanced Usage

### Custom Bench Commands

```bash
# Install additional app
docker-compose exec backend bench get-app [app-name]
docker-compose exec backend bench --site development.localhost install-app [app-name]

# Create new site
docker-compose exec backend bench new-site [site-name] \
  --mariadb-root-password admin \
  --admin-password admin

# Enable/disable maintenance mode
docker-compose exec backend bench --site development.localhost set-maintenance-mode on
docker-compose exec backend bench --site development.localhost set-maintenance-mode off
```

### Production Deployment

This setup is for **development only**. For production:

1. Use official Frappe Docker images
2. Set up proper SSL/TLS
3. Use environment secrets
4. Configure backups
5. Set up monitoring
6. Use production-grade configurations

See: https://github.com/frappe/frappe_docker

### Connecting External Tools

**Database Client:**
```bash
Host: localhost
Port: 3306 (expose in docker-compose.yml)
User: root
Password: admin (from .env)
```

**Redis Client:**
```bash
Host: localhost
Port: 6379 (expose in docker-compose.yml)
```

### Custom Dockerfile

To add system packages:

```dockerfile
# In Dockerfile, add under "Install system dependencies"
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    your-package \
    && rm -rf /var/lib/apt/lists/*
```

Then rebuild:
```bash
docker-compose build --no-cache
```

## Useful Commands Reference

```bash
# Docker Compose
docker-compose up -d              # Start services
docker-compose down               # Stop services
docker-compose down -v            # Stop and remove volumes
docker-compose ps                 # List services
docker-compose logs -f            # Follow logs
docker-compose restart [service]  # Restart service
docker-compose build              # Build images

# Bench
bench start                       # Start bench
bench restart                     # Restart bench
bench migrate                     # Run migrations
bench clear-cache                 # Clear cache
bench console                     # Python console
bench doctor                      # Check bench health

# Make
make help                         # Show all commands
make start                        # Start services
make stop                         # Stop services
make logs                         # View logs
make bash                         # Access bash
make console                      # Access console
```

## Support

For issues specific to:
- **Docker setup:** Check this guide and Docker documentation
- **Frappe/ERPNext:** See https://frappeframework.com/docs
- **Consignment Store app:** Check the main README.md

## License

gpl-2.0
