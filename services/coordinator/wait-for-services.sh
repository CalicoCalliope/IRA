#!/bin/bash
# Usage: ./wait-for-services.sh host1:port host2:port ... -- command args

set -e

# Separate service args from command
SERVICES=()
while [ "$1" != "--" ]; do
  SERVICES+=("$1")
  shift
done
shift

# Wait for each service
for s in "${SERVICES[@]}"; do
  host=$(echo $s | cut -d: -f1)
  port=$(echo $s | cut -d: -f2)
  echo "Waiting for $host:$port..."
  while ! nc -z $host $port; do
    sleep 1
  done
done

# Execute command
exec "$@"