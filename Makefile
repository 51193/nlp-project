.PHONY: run frontend check ruff database lint api start-all stop-all status clean-cache worker worker-start worker-stop worker-restart
.PHONY: docker-buildx-prepare docker-buildx-clean docker-buildx-reset
.PHONY: docker-push docker-push-latest docker-release tag export-docs

# Windows兼容的版本获取方式
ifeq ($(OS),Windows_NT)
    # Windows系统
    VERSION := $(shell powershell -Command "(Select-String -Path pyproject.toml -Pattern 'version = \"([^\"]*)\"').Matches.Groups[1].Value")
else
    # Linux/Mac系统
    VERSION := $(shell grep -m1 version pyproject.toml | cut -d'"' -f2)
endif

# Image names for both registries
DOCKERHUB_IMAGE := lfnovo/open_notebook
GHCR_IMAGE := ghcr.io/lfnovo/open-notebook

# Build platforms
PLATFORMS := linux/amd64,linux/arm64

database:
	docker compose up -d surrealdb

run:
	@echo "⚠️  Warning: Starting frontend only. For full functionality, use 'make start-all'"
	cd frontend; npm run dev

frontend:
	cd frontend; npm run dev

lint:
	uv run python -m mypy .

ruff:
	ruff check . --fix

# === Docker Build Setup ===
docker-buildx-prepare:
	@docker buildx inspect multi-platform-builder >nul 2>&1 || \
		docker buildx create --use --name multi-platform-builder --driver docker-container
	@docker buildx use multi-platform-builder

docker-buildx-clean:
	@echo "🧹 Cleaning up buildx builders..."
	@docker buildx rm multi-platform-builder 2>nul || true
	@echo "✅ Buildx cleanup complete!"

docker-buildx-reset: docker-buildx-clean docker-buildx-prepare
	@echo "✅ Buildx reset complete!"

# === Docker Build Targets ===

# Build and push version tags ONLY (no latest) for both regular and single images
docker-push: docker-buildx-prepare
	@echo "📤 Building and pushing version $(VERSION) to both registries..."
	@echo "🔨 Building regular image..."
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		--progress=plain \
		-t $(DOCKERHUB_IMAGE):$(VERSION) \
		-t $(GHCR_IMAGE):$(VERSION) \
		--push \
		.
	@echo "🔨 Building single-container image..."
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		--progress=plain \
		-f Dockerfile.single \
		-t $(DOCKERHUB_IMAGE):$(VERSION)-single \
		-t $(GHCR_IMAGE):$(VERSION)-single \
		--push \
		.
	@echo "✅ Pushed version $(VERSION) to both registries (latest NOT updated)"
	@echo "  📦 Docker Hub:"
	@echo "    - $(DOCKERHUB_IMAGE):$(VERSION)"
	@echo "    - $(DOCKERHUB_IMAGE):$(VERSION)-single"
	@echo "  📦 GHCR:"
	@echo "    - $(GHCR_IMAGE):$(VERSION)"
	@echo "    - $(GHCR_IMAGE):$(VERSION)-single"

# Update v1-latest tags to current version (both regular and single images)
docker-push-latest: docker-buildx-prepare
	@echo "📤 Updating v1-latest tags to version $(VERSION)..."
	@echo "🔨 Building regular image with latest tag..."
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		--progress=plain \
		-t $(DOCKERHUB_IMAGE):$(VERSION) \
		-t $(DOCKERHUB_IMAGE):v1-latest \
		-t $(GHCR_IMAGE):$(VERSION) \
		-t $(GHCR_IMAGE):v1-latest \
		--push \
		.
	@echo "🔨 Building single-container image with latest tag..."
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		--progress=plain \
		-f Dockerfile.single \
		-t $(DOCKERHUB_IMAGE):$(VERSION)-single \
		-t $(DOCKERHUB_IMAGE):v1-latest-single \
		-t $(GHCR_IMAGE):$(VERSION)-single \
		-t $(GHCR_IMAGE):v1-latest-single \
		--push \
		.
	@echo "✅ Updated v1-latest to version $(VERSION)"
	@echo "  📦 Docker Hub:"
	@echo "    - $(DOCKERHUB_IMAGE):$(VERSION) → v1-latest"
	@echo "    - $(DOCKERHUB_IMAGE):$(VERSION)-single → v1-latest-single"
	@echo "  📦 GHCR:"
	@echo "    - $(GHCR_IMAGE):$(VERSION) → v1-latest"
	@echo "    - $(GHCR_IMAGE):$(VERSION)-single → v1-latest-single"

# Full release: push version AND update latest tags
docker-release: docker-push-latest
	@echo "✅ Full release complete for version $(VERSION)"

tag:
	@echo "Creating tag v$(VERSION)"
	git tag "v$(VERSION)"
	git push origin "v$(VERSION)"

dev:
	docker compose -f docker-compose.dev.yml up --build 

full:
	docker compose -f docker-compose.full.yml up --build 

api:
	uv run run_api.py

# === Worker Management ===
.PHONY: worker worker-start worker-stop worker-restart

worker: worker-start

worker-start:
	@echo "Starting surreal-commands worker..."
	uv run --env-file .env surreal-commands-worker --import-modules commands

worker-stop:
	@echo "Stopping surreal-commands worker..."
	@taskkill /f /im python.exe /fi "windowtitle eq surreal-commands-worker*" 2>nul || true

worker-restart: worker-stop
	@timeout /t 2 /nobreak >nul
	@$(MAKE) worker-start

# === Service Management ===
start-all:
	@echo "🚀 Starting Open Notebook (Database + API + Worker + Frontend)..."
	@echo "📊 Starting SurrealDB..."
	@docker compose up -d surrealdb
# 	@timeout /t 15 /nobreak >nul 
# 	@sleep 3
	@echo "🔧 Starting API backend..."
	@nohup uv run run_api.py > api.log 2>&1 &
	@echo "Waiting for API to start..."
	
	@timeout 30 bash -c 'until nc -z localhost 5055; do sleep 1; done' || echo "Warning: API may not be ready"
	@sleep 2
	
# 	@uv run run_api.py &
# 	@nohup uv run run_api.py > api.log 2>&1 &
# 	@uv run run_api.py > api.log 2>&1 &
# 	@sleep 3
	@echo "⚙️ Starting background worker..."
# 	@uv run --env-file .env surreal-commands-worker --import-modules commands &
# 	@echo "⚙️ Starting background worker..."
	@nohup uv run --env-file .env surreal-commands-worker --import-modules commands > worker.log 2>&1 &
# 	@start "Background Worker" cmd /c "uv run --env-file .env surreal-commands-worker --import-modules commands"
# 	@sleep 2
	@echo "🌐 Starting Next.js frontend..."
	@echo "✅ All services started!"
	@echo "📱 Frontend: http://localhost:3000"
	@echo "🔗 API: http://localhost:5055"
	@echo "📚 API Docs: http://localhost:5055/docs"
	@cd frontend && npm run dev

stop-all:
	@echo "🛑 Stopping all Open Notebook services..."
	@taskkill /f /im node.exe 2>nul || true
	@taskkill /f /im python.exe 2>nul || true
	@docker compose down
	@echo "✅ All services stopped!"

status:
	@echo "📊 Open Notebook Service Status:"
	@echo "Database (SurrealDB):"
	@docker compose ps surrealdb 2>nul || echo "  ❌ Not running"
	@echo "API Backend:"
	@tasklist /fi "windowtitle eq API Backend*" 2>nul | findstr /c:"cmd.exe" >nul && echo "  ✅ Running" || echo "  ❌ Not running"
	@echo "Background Worker:"
	@tasklist /fi "windowtitle eq Background Worker*" 2>nul | findstr /c:"cmd.exe" >nul && echo "  ✅ Running" || echo "  ❌ Not running"
	@echo "Next.js Frontend:"
	@tasklist /fi "imagename eq node.exe" 2>nul | findstr /c:"node.exe" >nul && echo "  ✅ Running" || echo "  ❌ Not running"

# === Documentation Export ===
export-docs:
	@echo "📚 Exporting documentation..."
	@uv run python scripts/export_docs.py
	@echo "✅ Documentation export complete!"

# === Cleanup ===
clean-cache:
	@echo "🧹 Cleaning cache directories..."
	@rmdir /s /q __pycache__ 2>nul || true
	@rmdir /s /q .mypy_cache 2>nul || true
	@rmdir /s /q .ruff_cache 2>nul || true
	@rmdir /s /q .pytest_cache 2>nul || true
	@del /s /q *.pyc 2>nul || true
	@del /s /q *.pyo 2>nul || true
	@del /s /q *.pyd 2>nul || true
	@echo "✅ Cache directories cleaned!"

# ======================================================================================================================

# .PHONY: run frontend check ruff database lint api start-all stop-all status clean-cache worker worker-start worker-stop worker-restart
# .PHONY: docker-buildx-prepare docker-buildx-clean docker-buildx-reset
# .PHONY: docker-push docker-push-latest docker-release tag export-docs

# # Get version from pyproject.toml
# VERSION := $(shell grep -m1 version pyproject.toml | cut -d'"' -f2)

# # Image names for both registries
# DOCKERHUB_IMAGE := lfnovo/open_notebook
# GHCR_IMAGE := ghcr.io/lfnovo/open-notebook

# # Build platforms
# PLATFORMS := linux/amd64,linux/arm64

# database:
# 	docker compose up -d surrealdb

# run:
# 	@echo "⚠️  Warning: Starting frontend only. For full functionality, use 'make start-all'"
# 	cd frontend && npm run dev

# frontend:
# 	cd frontend && npm run dev

# lint:
# 	uv run python -m mypy .

# ruff:
# 	ruff check . --fix

# # === Docker Build Setup ===
# docker-buildx-prepare:
# 	@docker buildx inspect multi-platform-builder >/dev/null 2>&1 || \
# 		docker buildx create --use --name multi-platform-builder --driver docker-container
# 	@docker buildx use multi-platform-builder

# docker-buildx-clean:
# 	@echo "🧹 Cleaning up buildx builders..."
# 	@docker buildx rm multi-platform-builder 2>/dev/null || true
# 	@docker ps -a | grep buildx_buildkit | awk '{print $$1}' | xargs -r docker rm -f 2>/dev/null || true
# 	@echo "✅ Buildx cleanup complete!"

# docker-buildx-reset: docker-buildx-clean docker-buildx-prepare
# 	@echo "✅ Buildx reset complete!"

# # === Docker Build Targets ===

# # Build and push version tags ONLY (no latest) for both regular and single images
# docker-push: docker-buildx-prepare
# 	@echo "📤 Building and pushing version $(VERSION) to both registries..."
# 	@echo "🔨 Building regular image..."
# 	docker buildx build --pull \
# 		--platform $(PLATFORMS) \
# 		--progress=plain \
# 		-t $(DOCKERHUB_IMAGE):$(VERSION) \
# 		-t $(GHCR_IMAGE):$(VERSION) \
# 		--push \
# 		.
# 	@echo "🔨 Building single-container image..."
# 	docker buildx build --pull \
# 		--platform $(PLATFORMS) \
# 		--progress=plain \
# 		-f Dockerfile.single \
# 		-t $(DOCKERHUB_IMAGE):$(VERSION)-single \
# 		-t $(GHCR_IMAGE):$(VERSION)-single \
# 		--push \
# 		.
# 	@echo "✅ Pushed version $(VERSION) to both registries (latest NOT updated)"
# 	@echo "  📦 Docker Hub:"
# 	@echo "    - $(DOCKERHUB_IMAGE):$(VERSION)"
# 	@echo "    - $(DOCKERHUB_IMAGE):$(VERSION)-single"
# 	@echo "  📦 GHCR:"
# 	@echo "    - $(GHCR_IMAGE):$(VERSION)"
# 	@echo "    - $(GHCR_IMAGE):$(VERSION)-single"

# # Update v1-latest tags to current version (both regular and single images)
# docker-push-latest: docker-buildx-prepare
# 	@echo "📤 Updating v1-latest tags to version $(VERSION)..."
# 	@echo "🔨 Building regular image with latest tag..."
# 	docker buildx build --pull \
# 		--platform $(PLATFORMS) \
# 		--progress=plain \
# 		-t $(DOCKERHUB_IMAGE):$(VERSION) \
# 		-t $(DOCKERHUB_IMAGE):v1-latest \
# 		-t $(GHCR_IMAGE):$(VERSION) \
# 		-t $(GHCR_IMAGE):v1-latest \
# 		--push \
# 		.
# 	@echo "🔨 Building single-container image with latest tag..."
# 	docker buildx build --pull \
# 		--platform $(PLATFORMS) \
# 		--progress=plain \
# 		-f Dockerfile.single \
# 		-t $(DOCKERHUB_IMAGE):$(VERSION)-single \
# 		-t $(DOCKERHUB_IMAGE):v1-latest-single \
# 		-t $(GHCR_IMAGE):$(VERSION)-single \
# 		-t $(GHCR_IMAGE):v1-latest-single \
# 		--push \
# 		.
# 	@echo "✅ Updated v1-latest to version $(VERSION)"
# 	@echo "  📦 Docker Hub:"
# 	@echo "    - $(DOCKERHUB_IMAGE):$(VERSION) → v1-latest"
# 	@echo "    - $(DOCKERHUB_IMAGE):$(VERSION)-single → v1-latest-single"
# 	@echo "  📦 GHCR:"
# 	@echo "    - $(GHCR_IMAGE):$(VERSION) → v1-latest"
# 	@echo "    - $(GHCR_IMAGE):$(VERSION)-single → v1-latest-single"

# # Full release: push version AND update latest tags
# docker-release: docker-push-latest
# 	@echo "✅ Full release complete for version $(VERSION)"

# tag:
# 	@version=$$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'); \
# 	echo "Creating tag v$$version"; \
# 	git tag "v$$version"; \
# 	git push origin "v$$version"


# dev:
# 	docker compose -f docker-compose.dev.yml up --build 

# full:
# 	docker compose -f docker-compose.full.yml up --build 


# api:
# 	uv run run_api.py

# # === Worker Management ===
# .PHONY: worker worker-start worker-stop worker-restart

# worker: worker-start

# worker-start:
# 	@echo "Starting surreal-commands worker..."
# 	uv run --env-file .env surreal-commands-worker --import-modules commands

# worker-stop:
# 	@echo "Stopping surreal-commands worker..."
# 	pkill -f "surreal-commands-worker" || true

# worker-restart: worker-stop
# 	@sleep 2
# 	@$(MAKE) worker-start

# # === Service Management ===
# start-all:
# 	@echo "🚀 Starting Open Notebook (Database + API + Worker + Frontend)..."
# 	@echo "📊 Starting SurrealDB..."
# 	@docker compose up -d surrealdb
# 	@sleep 3
# 	@echo "🔧 Starting API backend..."
# 	@uv run run_api.py &
# 	@sleep 3
# 	@echo "⚙️ Starting background worker..."
# 	@uv run --env-file .env surreal-commands-worker --import-modules commands &
# 	@sleep 2
# 	@echo "🌐 Starting Next.js frontend..."
# 	@echo "✅ All services started!"
# 	@echo "📱 Frontend: http://localhost:3000"
# 	@echo "🔗 API: http://localhost:5055"
# 	@echo "📚 API Docs: http://localhost:5055/docs"
# 	cd frontend && npm run dev

# stop-all:
# 	@echo "🛑 Stopping all Open Notebook services..."
# 	@pkill -f "next dev" || true
# 	@pkill -f "surreal-commands-worker" || true
# 	@pkill -f "run_api.py" || true
# 	@pkill -f "uvicorn api.main:app" || true
# 	@docker compose down
# 	@echo "✅ All services stopped!"

# status:
# 	@echo "📊 Open Notebook Service Status:"
# 	@echo "Database (SurrealDB):"
# 	@docker compose ps surrealdb 2>/dev/null || echo "  ❌ Not running"
# 	@echo "API Backend:"
# 	@pgrep -f "run_api.py\|uvicorn api.main:app" >/dev/null && echo "  ✅ Running" || echo "  ❌ Not running"
# 	@echo "Background Worker:"
# 	@pgrep -f "surreal-commands-worker" >/dev/null && echo "  ✅ Running" || echo "  ❌ Not running"
# 	@echo "Next.js Frontend:"
# 	@pgrep -f "next dev" >/dev/null && echo "  ✅ Running" || echo "  ❌ Not running"

# # === Documentation Export ===
# export-docs:
# 	@echo "📚 Exporting documentation..."
# 	@uv run python scripts/export_docs.py
# 	@echo "✅ Documentation export complete!"

# # === Cleanup ===
# clean-cache:
# 	@echo "🧹 Cleaning cache directories..."
# 	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
# 	@find . -name ".mypy_cache" -type d -exec rm -rf {} + 2>/dev/null || true
# 	@find . -name ".ruff_cache" -type d -exec rm -rf {} + 2>/dev/null || true
# 	@find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
# 	@find . -name "*.pyc" -type f -delete 2>/dev/null || true
# 	@find . -name "*.pyo" -type f -delete 2>/dev/null || true
# 	@find . -name "*.pyd" -type f -delete 2>/dev/null || true
# 	@echo "✅ Cache directories cleaned!"