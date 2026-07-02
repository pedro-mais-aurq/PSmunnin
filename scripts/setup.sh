#!/bin/bash
set -e

echo "Setup LeadHunter AI"

pip install -e packages/domain-core
pip install -e packages/agents-toolkit
pip install -e packages/shared-sdk
pip install -e apps/api
pip install -e apps/worker

cd apps/web && npm install

echo "Setup completo"
