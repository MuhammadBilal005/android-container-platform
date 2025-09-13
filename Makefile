.PHONY: setup dev build deploy clean test

# Setup development environment
setup:
	@echo "Setting up Android Container Platform..."
	@command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
	@command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed. Aborting." >&2; exit 1; }
	@echo "Creating required directories..."
	@mkdir -p data/android-instances data/logs data/backups
	@mkdir -p config/device-profiles config/network config/apps
	@echo "Building base images..."
	docker-compose build
	@echo "Setup complete! Run 'make dev' to start the platform."

# Start development environment
dev:
	@echo "Starting development environment..."
	docker-compose up -d
	@echo "Platform started! Dashboard available at http://localhost:8080"
	@echo "API available at http://localhost:3000"

# Build all images
build:
	docker-compose build --no-cache

# Deploy to production (requires kubectl configured)
deploy:
	@echo "Deploying to production..."
	kubectl apply -f k8s/

# Clean up everything
clean:
	docker-compose down -v
	docker system prune -f
	rm -rf data/android-instances/*
	rm -rf data/logs/*

# Run tests
test:
	@echo "Running integrity bypass tests..."
	./scripts/test-integrity.sh
	@echo "Running performance tests..."
	./scripts/test-performance.sh

# Show logs
logs:
	docker-compose logs -f

# Stop all services
stop:
	docker-compose down

# Restart services
restart: stop dev