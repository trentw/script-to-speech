.PHONY: gui-server gui-dev gui-desktop gui-build gui-build-debug gui-build-release gui-build-backend kill-server check-gui-deps
.PHONY: frontend-test frontend-test-ui frontend-test-coverage frontend-lint frontend-lint-fix
.PHONY: frontend-format frontend-type-check frontend-analyze frontend-type-coverage help
.PHONY: website-dev website-build website-preview
.PHONY: bump-patch bump-minor bump-major bump-dry-run check-version release

help: ## Show available commands
	@echo "Script-to-Speech GUI Commands:"
	@echo "  make gui-server         - Start FastAPI backend server"
	@echo "  make kill-server        - Stop FastAPI backend server"
	@echo "  make gui-dev            - Start React frontend (web, recommended for development)"
	@echo "  make gui-desktop        - Start desktop app in development mode"
	@echo "  make gui-build          - Build production desktop app (debug mode, default)"
	@echo "  make gui-build-debug    - Build production desktop app (debug mode, with console)"
	@echo "  make gui-build-release  - Build production desktop app (release mode, optimized)"
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
	@echo "Website Commands:"
	@echo "  make website-dev        - Start website development server"
	@echo "  make website-build      - Build website for production"
	@echo "  make website-preview    - Preview production build locally"
	@echo ""
	@echo "Versioning Commands:"
	@echo "  make bump-patch         - Bump patch version (e.g., 2.0.0 -> 2.0.1)"
	@echo "  make bump-minor         - Bump minor version (e.g., 2.0.0 -> 2.1.0)"
	@echo "  make bump-major         - Bump major version (e.g., 2.0.0 -> 3.0.0)"
	@echo "  make bump-dry-run       - Preview what a patch bump would change"
	@echo "  make check-version      - Verify all version files are in sync"
	@echo "  make release            - Show instructions to push release tag"
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

check-gui-deps: ## Verify GUI build dependencies are installed
	@command -v node >/dev/null 2>&1 || { echo "❌ Error: Node.js is required but not found."; echo "   Install with: brew install node (macOS) or visit https://nodejs.org/"; exit 1; }
	@command -v pnpm >/dev/null 2>&1 || { echo "❌ Error: pnpm is required but not found."; echo "   Install with: npm install -g pnpm"; exit 1; }
	@command -v cargo >/dev/null 2>&1 || { echo "❌ Error: Rust is required but not found."; echo "   Install with: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"; exit 1; }
	@if [ ! -d "gui/frontend/node_modules" ]; then echo "📦 Installing frontend dependencies..."; cd gui/frontend && pnpm install; fi

gui-dev: check-gui-deps ## Start React frontend for web development
	cd gui/frontend && pnpm run dev


gui-desktop: check-gui-deps ## Start desktop app in development mode
	cd gui/frontend && pnpm run tauri dev

gui-build: gui-build-debug ## Build production desktop app (defaults to debug mode)

gui-build-debug: check-gui-deps ## Build production desktop app with debug mode (console access)
	@echo "🔨 Building backend executable..."
	@uv run --extra build --extra gui python build_backend.py
	@echo "🏗️  Building Tauri app (debug mode - has console for easier debugging)..."
	@cd gui/frontend && pnpm run tauri build --debug

gui-build-release: check-gui-deps ## Build production desktop app (optimized release)
	@echo "🔨 Building backend executable..."
	@uv run --extra build --extra gui python build_backend.py
	@echo "🏗️  Building Tauri app (release mode - optimized)..."
	@cd gui/frontend && pnpm run tauri build

gui-build-backend: ## Build standalone backend executable
	uv run --extra build --extra gui python build_backend.py

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

# Versioning Commands
bump-patch: ## Bump patch version (e.g., 2.0.0 -> 2.0.1), commits and tags
	uv run bump-my-version bump patch

bump-minor: ## Bump minor version (e.g., 2.0.0 -> 2.1.0), commits and tags
	uv run bump-my-version bump minor

bump-major: ## Bump major version (e.g., 2.0.0 -> 3.0.0), commits and tags
	uv run bump-my-version bump major

bump-dry-run: ## Preview what a patch bump would change (no modifications)
	uv run bump-my-version bump --dry-run -vv patch

check-version: ## Verify all version files are in sync
	uv run python scripts/check_version_sync.py

release: ## Show instructions to push latest release tag
	@echo ""
	@echo "To trigger a GitHub release build, push the tag:"
	@echo "  git push origin master --tags"
	@echo ""
	@echo "This will trigger the build-desktop workflow which creates"
	@echo "a draft GitHub release with binaries for all platforms."

# Website Commands
website-dev: ## Start website development server
	cd website && pnpm run dev

website-build: ## Build website for production
	cd website && pnpm run build

website-preview: ## Preview production build locally
	cd website && pnpm run preview
