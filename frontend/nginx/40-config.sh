#!/bin/sh
# Генерує config.js з адресою API для поточного середовища.
set -e
cat > /usr/share/nginx/html/config.js <<CFG
window.APP_CONFIG = { apiBaseUrl: "${API_BASE_URL:-/api}" };
CFG
echo "frontend: apiBaseUrl=${API_BASE_URL:-/api}, upstream=${API_UPSTREAM}"
