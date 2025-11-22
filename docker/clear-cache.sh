#!/bin/bash
# Clear cache for the site

SITE_NAME="${SITE_NAME:-development.localhost}"

echo "Clearing cache for site: ${SITE_NAME}"
docker-compose exec backend bench --site ${SITE_NAME} clear-cache
