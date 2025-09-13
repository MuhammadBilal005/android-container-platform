#!/bin/sh

# Docker entrypoint script for environment variable injection

# Create environment configuration file
cat <<EOF > /usr/share/nginx/html/env-config.js
window._env_ = {
  REACT_APP_API_URL: "${REACT_APP_API_URL:-http://localhost:3000}",
  REACT_APP_WS_URL: "${REACT_APP_WS_URL:-http://localhost:3000}",
  REACT_APP_MAP_PROVIDER: "${REACT_APP_MAP_PROVIDER:-openstreetmap}",
  REACT_APP_MAP_API_KEY: "${REACT_APP_MAP_API_KEY:-}",
  REACT_APP_APP_NAME: "${REACT_APP_APP_NAME:-Android Container Platform}",
  REACT_APP_VERSION: "${REACT_APP_VERSION:-1.0.0}",
  REACT_APP_ENVIRONMENT: "${REACT_APP_ENVIRONMENT:-production}",
  REACT_APP_ENABLE_DEBUG: "${REACT_APP_ENABLE_DEBUG:-false}",
  REACT_APP_ENABLE_ANALYTICS: "${REACT_APP_ENABLE_ANALYTICS:-false}",
  REACT_APP_CACHE_TIMEOUT: "${REACT_APP_CACHE_TIMEOUT:-300000}",
  REACT_APP_MAX_LOG_ENTRIES: "${REACT_APP_MAX_LOG_ENTRIES:-1000}",
  REACT_APP_REFRESH_INTERVAL: "${REACT_APP_REFRESH_INTERVAL:-30000}",
  REACT_APP_WEBSOCKET_TIMEOUT: "${REACT_APP_WEBSOCKET_TIMEOUT:-20000}"
};
EOF

# Replace environment placeholders in index.html
sed -i 's|</head>|<script src="/env-config.js"></script></head>|' /usr/share/nginx/html/index.html

# Start nginx
exec "$@"