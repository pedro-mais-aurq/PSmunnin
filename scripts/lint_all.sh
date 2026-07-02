#!/bin/bash
set -e

echo "Linting..."
cd apps/api && ruff check src
cd ../worker && ruff check src
cd ../web && npm run lint

echo "Lint OK"
