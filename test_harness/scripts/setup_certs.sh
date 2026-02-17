#!/usr/bin/env bash
# Entrypoint wrapper: copy SSL certs into position BEFORE PostgreSQL starts.
#
# The standard PostgreSQL Docker entrypoint starts a temporary postgres instance
# (with the same command-line flags) to run /docker-entrypoint-initdb.d/ scripts.
# If ssl=on is in the command flags, that temporary instance needs the cert files
# to already exist. Running cert setup as an init script is too late - postgres
# has already tried (and failed) to load the certs.
#
# This wrapper runs first, copies certs from the staging mount, then delegates
# to the standard entrypoint so everything else (initdb, init scripts, final
# postgres startup) proceeds normally.

set -e

if [ -d /certs-staging ] && [ -f /certs-staging/server.crt ]; then
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
    echo "pgmonkey-harness: WARNING - No /certs-staging found, SSL certs not set up."
fi

# Delegate to the standard PostgreSQL Docker entrypoint
exec docker-entrypoint.sh "$@"
