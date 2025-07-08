.PHONY: gui-server gui-dev gui-desktop gui-build gui-build-backend help

help: ## Show available commands
	@echo "Script-to-Speech GUI Commands:"
	@echo "  make gui-server         - Start FastAPI backend server"
	@echo "  make gui-dev            - Start React frontend (web, recommended for development)"  
	@echo "  make gui-desktop        - Start desktop app in development mode"
	@echo "  make gui-build          - Build production desktop app with bundled backend"
	@echo "  make gui-build-backend  - Build standalone backend executable only"
	@echo ""
	@echo "Development workflow:"
	@echo "  Terminal 1: make gui-server"
	@echo "  Terminal 2: make gui-dev (then open http://localhost:5173)"

gui-server: ## Start FastAPI backend server
	uv run sts-gui-server

gui-dev: ## Start React frontend for web development
	cd gui/frontend && npm run dev

gui-desktop: ## Start desktop app in development mode  
	cd gui/frontend && npx tauri dev

gui-build: ## Build production desktop app
	cd gui/frontend && npx tauri build

gui-build-backend: ## Build standalone backend executable
	uv run python build_backend.py