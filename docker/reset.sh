#!/bin/bash
# Reset the entire development environment (WARNING: This will delete all data!)

RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${RED}WARNING: This will delete all data including the database!${NC}"
echo -e "${YELLOW}Are you sure you want to continue? (yes/no)${NC}"
read -r confirmation

if [ "$confirmation" != "yes" ]; then
    echo "Reset cancelled."
    exit 0
fi

echo "Stopping all containers..."
docker-compose down

echo "Removing all volumes..."
docker-compose down -v

echo "Removing site directory..."
sudo rm -rf sites/*

echo "Reset complete. Run ./setup.sh to set up the environment again."
