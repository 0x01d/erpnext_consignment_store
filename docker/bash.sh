#!/bin/bash
# Access bash shell in the backend container

echo "Opening bash shell in backend container..."
docker-compose exec backend bash
