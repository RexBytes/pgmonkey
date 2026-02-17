#!/usr/bin/env bash
# Generate SSL certificates for pgmonkey test harness
#
# Creates:
#   ca.key / ca.crt           - Self-signed Certificate Authority
#   server.key / server.crt   - Server cert (SAN: localhost, pg-ssl, pg-clientcert)
#   client.key / client.crt   - Client cert (CN=pgmonkey_user, for client cert auth)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CERTS_DIR="$(dirname "$SCRIPT_DIR")/certs"

echo "Generating SSL certificates in $CERTS_DIR ..."
mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

# --- Certificate Authority ---
echo "  [1/3] Creating CA ..."
openssl genrsa -out ca.key 2048 2>/dev/null
openssl req -new -x509 -days 365 -key ca.key -out ca.crt \
    -subj "/CN=pgmonkey-test-ca/O=pgmonkey-test" 2>/dev/null

# --- Server Certificate ---
echo "  [2/3] Creating server certificate ..."
openssl genrsa -out server.key 2048 2>/dev/null

# Create SAN config for server cert
cat > server_ext.cnf <<'EXTCNF'
[req]
distinguished_name = req_dn
req_extensions = v3_req
prompt = no

[req_dn]
CN = localhost
O = pgmonkey-test

[v3_req]
subjectAltName = DNS:localhost,DNS:pg-ssl,DNS:pg-clientcert,IP:127.0.0.1

[v3_ca]
subjectAltName = DNS:localhost,DNS:pg-ssl,DNS:pg-clientcert,IP:127.0.0.1
EXTCNF

openssl req -new -key server.key -out server.csr \
    -config server_ext.cnf 2>/dev/null
openssl x509 -req -days 365 -in server.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out server.crt \
    -extfile server_ext.cnf -extensions v3_ca 2>/dev/null

# --- Client Certificate ---
echo "  [3/3] Creating client certificate (CN=pgmonkey_user) ..."
openssl genrsa -out client.key 2048 2>/dev/null
openssl req -new -key client.key -out client.csr \
    -subj "/CN=pgmonkey_user/O=pgmonkey-test" 2>/dev/null
openssl x509 -req -days 365 -in client.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out client.crt 2>/dev/null

# --- Cleanup temp files ---
rm -f *.csr *.cnf *.srl

# --- Set permissions ---
chmod 600 server.key client.key ca.key
chmod 644 server.crt client.crt ca.crt

echo "  Certificates generated:"
ls -la "$CERTS_DIR"
echo "  Done."
