.PHONY: gui-server gui-dev gui-desktop gui-build gui-build-backend kill-server
.PHONY: frontend-test frontend-test-ui frontend-test-coverage frontend-lint frontend-lint-fix
.PHONY: frontend-format frontend-type-check frontend-analyze frontend-type-coverage help

help: ## Show available commands
	@echo "Script-to-Speech GUI Commands:"
	@echo "  make gui-server         - Start FastAPI backend server"
	@echo "  make kill-server        - Stop FastAPI backend server"
	@echo "  make gui-dev            - Start React frontend (web, recommended for development)"  
	@echo "  make gui-desktop        - Start desktop app in development mode"
	@echo "  make gui-build          - Build production desktop app with bundled backend"
	@echo "  make gui-build-backend  - Build standalone backend executable only"
	@echo ""
	@echo "Frontend Development Commands:"
	@echo "  make frontend-test      - Run frontend tests"
	@echo "  make frontend-test-ui   - Run tests with UI interface"
	@echo "  make frontend-test-coverage - Run tests with coverage report"
	@echo "  make frontend-lint      - Run ESLint checks"
	@echo "  make frontend-lint-fix  - Run ESLint with auto-fix"
	@echo "  make frontend-format    - Run Prettier formatting"
	@echo "  make frontend-type-check - Run TypeScript type checking"
	@echo "  make frontend-analyze   - Generate bundle analysis"
	@echo "  make frontend-type-coverage - Check TypeScript type coverage"
	@echo ""
	@echo "Development workflow:"
	@echo "  Terminal 1: make gui-server"
	@echo "  Terminal 2: make gui-dev (then open http://localhost:5173)"

gui-server: ## Start FastAPI backend server
	uv run sts-gui-server

kill-server: ## Stop FastAPI backend server
	@PIDS=$$(lsof -t -i:8000); \
	if [ -n "$$PIDS" ]; then \
		echo "Force-killing backend server process(es)..."; \
		echo "$$PIDS" | xargs kill -9; \
		echo "Backend server process(es) killed."; \
	else \
		echo "Backend server is not running."; \
	fi

gui-dev: ## Start React frontend for web development
	cd gui/frontend && pnpm run dev


gui-desktop: ## Start desktop app in development mode  
	cd gui/frontend && npx tauri dev

gui-build: ## Build production desktop app
	cd gui/frontend && npx tauri build

gui-build-backend: ## Build standalone backend executable
	uv run python build_backend.py

# Frontend Development Commands
frontend-test: ## Run frontend tests
	cd gui/frontend && pnpm run test

frontend-test-ui: ## Run tests with UI interface
	cd gui/frontend && pnpm run test:ui

frontend-test-coverage: ## Run tests with coverage report
	cd gui/frontend && pnpm run test:coverage

frontend-lint: ## Run ESLint checks
	cd gui/frontend && pnpm run lint

frontend-lint-fix: ## Run ESLint with auto-fix
	cd gui/frontend && pnpm run lint:fix

frontend-format: ## Run Prettier formatting
	cd gui/frontend && pnpm run format

frontend-type-check: ## Run TypeScript type checking
	cd gui/frontend && pnpm run type-check

frontend-analyze: ## Generate bundle analysis
	cd gui/frontend && pnpm run analyze

frontend-type-coverage: ## Check TypeScript type coverage
	cd gui/frontend && pnpm run type-coverage