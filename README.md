# =========================================================
# PS Munnin - .gitignore
# Backend: Python / FastAPI
# Frontend: React / CRACO
# =========================================================


# =========================================================
# Environment files - NEVER COMMIT REAL SECRETS
# =========================================================
.env
*.env
.env.*
*.env.*

backend/.env
backend/*.env
backend/.env.*

frontend/.env
frontend/*.env
frontend/.env.*

# Keep safe examples
!.env.example
!backend/.env.example
!frontend/.env.example


# =========================================================
# Python / FastAPI
# =========================================================
__pycache__/
*/__pycache__/
*.py[cod]
*$py.class

*.pyo
*.pyd
*.so

.Python
.python-version

# Virtual environments
.venv/
venv/
env/
ENV/
backend/.venv/
backend/venv/
backend/env/

# Python packaging/build
build/
dist/
*.egg-info/
.eggs/
pip-wheel-metadata/

# Test / coverage / type checking
.pytest_cache/
.coverage
.coverage.*
htmlcov/
.tox/
.nox/
.mypy_cache/
.pyre/
.pytype/
.ruff_cache/


# =========================================================
# Node / React / CRACO
# =========================================================
node_modules/
frontend/node_modules/

# React build output
frontend/build/
frontend/.cache/

# Package manager cache/logs
.npm/
.pnpm-store/
.yarn/
.yarn-cache/
.yarnrc.yml

npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*

# Keep lockfiles
!package-lock.json
!frontend/package-lock.json


# =========================================================
# Logs
# =========================================================
logs/
*.log


# =========================================================
# Mongo / local database dumps
# =========================================================
dump/
dumps/
*.bson
*.archive
*.mongodb


# =========================================================
# OS files
# =========================================================
.DS_Store
.AppleDouble
.LSOverride

Thumbs.db
Thumbs.db:encryptable
ehthumbs.db
ehthumbs_vista.db
Desktop.ini

$RECYCLE.BIN/


# =========================================================
# Editor / IDE
# =========================================================
.vscode/
.idea/
*.swp
*.swo
*.swn

# Optional: keep shared VS Code settings if you create them later
!.vscode/extensions.json
!.vscode/settings.example.json


# =========================================================
# Local temporary files
# =========================================================
tmp/
temp/
.cache/
.cache-loader/

*.tmp
*.temp
*.bak
*.backup
*.old


# =========================================================
# Deployment artifacts
# =========================================================
.vercel/
.netlify/
.render/


# =========================================================
# Misc
# =========================================================
*.zip
*.rar
*.7z
