#!/bin/bash
# Rebuild the consignment_store app after making changes

SITE_NAME="${SITE_NAME:-development.localhost}"

echo "Rebuilding consignment_store app..."

# Reinstall app dependencies
echo "Installing app dependencies..."
docker-compose exec backend bash -c "cd apps/consignment_store && pip3 install -e ."

# Clear cache
echo "Clearing cache..."
docker-compose exec backend bench --site ${SITE_NAME} clear-cache

# Run migrations
echo "Running migrations..."
docker-compose exec backend bench --site ${SITE_NAME} migrate

# Restart services
echo "Restarting services..."
docker-compose restart backend scheduler worker-short worker-long

echo "App rebuild complete!"
