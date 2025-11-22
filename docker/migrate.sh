#!/bin/bash
# Run database migrations

SITE_NAME="${SITE_NAME:-development.localhost}"

echo "Running migrations for site: ${SITE_NAME}"
docker-compose exec backend bench --site ${SITE_NAME} migrate
