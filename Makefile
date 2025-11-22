# Makefile for Consignment Store Development Environment
# Provides convenient shortcuts for common Docker operations

.PHONY: help setup start stop restart logs bash console migrate clear-cache rebuild reset

help: ## Show this help message
	@echo "Consignment Store Development Environment"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Initial setup - build and start the development environment
	./setup.sh

start: ## Start all services
	docker-compose up -d

stop: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View logs from all services (Ctrl+C to exit)
	docker-compose logs -f

bash: ## Open bash shell in backend container
	./docker/bash.sh

console: ## Open Frappe console
	./docker/console.sh

migrate: ## Run database migrations
	./docker/migrate.sh

clear-cache: ## Clear Frappe cache
	./docker/clear-cache.sh

rebuild: ## Rebuild the consignment_store app
	./docker/rebuild-app.sh

reset: ## Reset entire environment (WARNING: deletes all data)
	./docker/reset.sh

status: ## Show status of all services
	docker-compose ps

build: ## Build Docker images
	docker-compose build
