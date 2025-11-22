#!/bin/bash
# Access Frappe/ERPNext console for the site

SITE_NAME="${SITE_NAME:-development.localhost}"

echo "Opening Frappe console for site: ${SITE_NAME}"
docker-compose exec backend bench --site ${SITE_NAME} console
