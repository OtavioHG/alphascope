#!/usr/bin/env bash
set -euo pipefail

echo "Starting AlphaScope core services..."
docker compose -f deployment/docker/docker-compose.production.yml up -d postgres redis
echo "Core services started."
