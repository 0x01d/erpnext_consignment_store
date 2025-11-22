#!/bin/bash
# View logs from all services

SERVICE="${1:-}"

if [ -z "$SERVICE" ]; then
    echo "Following logs from all services..."
    docker-compose logs -f
else
    echo "Following logs from service: ${SERVICE}"
    docker-compose logs -f ${SERVICE}
fi
