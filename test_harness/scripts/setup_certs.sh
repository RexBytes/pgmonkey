#!/usr/bin/env bash
# Docker init script: copy SSL certs with correct ownership/permissions.
# Runs inside the PostgreSQL container during first-time initialization.
# Mounted at /docker-entrypoint-initdb.d/00_setup_certs.sh

set -e

if [ -d /certs-staging ]; then
    echo "pgmonkey-harness: Setting up SSL certificates ..."
    mkdir -p /var/lib/postgresql/certs
    cp /certs-staging/server.crt /var/lib/postgresql/certs/
    cp /certs-staging/server.key /var/lib/postgresql/certs/
    cp /certs-staging/ca.crt /var/lib/postgresql/certs/
    chmod 600 /var/lib/postgresql/certs/server.key
    chmod 644 /var/lib/postgresql/certs/server.crt /var/lib/postgresql/certs/ca.crt
    chown -R postgres:postgres /var/lib/postgresql/certs
    echo "pgmonkey-harness: SSL certificates ready."
else
    echo "pgmonkey-harness: No /certs-staging found, skipping SSL setup."
fi
