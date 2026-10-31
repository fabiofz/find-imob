#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
TLS_DIR="$PWD/.tls"
mkdir -p "$TLS_DIR"
chmod 700 "$TLS_DIR"

if [[ ! -s "$TLS_DIR/findimob-root-ca.key" || ! -s "$TLS_DIR/findimob-root-ca.crt" ]]; then
    openssl req -x509 -newkey rsa:4096 -nodes \
        -keyout "$TLS_DIR/findimob-root-ca.key" \
        -out "$TLS_DIR/findimob-root-ca.crt" \
        -days 3650 -sha256 \
        -subj "/CN=Find Imob Local Root CA" \
        -addext "basicConstraints=critical,CA:TRUE" \
        -addext "keyUsage=critical,keyCertSign,cRLSign"
    chmod 600 "$TLS_DIR/findimob-root-ca.key"
    chmod 644 "$TLS_DIR/findimob-root-ca.crt"
fi

if [[ ! -s "$TLS_DIR/server.key" || ! -s "$TLS_DIR/server.crt" ]] \
    || ! openssl x509 -in "$TLS_DIR/server.crt" -checkend 2592000 -noout >/dev/null 2>&1; then
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out "$TLS_DIR/server.key"
    openssl req -new -key "$TLS_DIR/server.key" -out "$TLS_DIR/server.csr" \
        -subj "/CN=findimob.local"
    cat > "$TLS_DIR/server.ext" <<'EXT'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:findimob.local,DNS:localhost,IP:127.0.0.1
EXT
    openssl x509 -req -in "$TLS_DIR/server.csr" \
        -CA "$TLS_DIR/findimob-root-ca.crt" \
        -CAkey "$TLS_DIR/findimob-root-ca.key" \
        -CAcreateserial -out "$TLS_DIR/server.crt" \
        -days 397 -sha256 -extfile "$TLS_DIR/server.ext"
    chmod 600 "$TLS_DIR/server.key"
    chmod 644 "$TLS_DIR/server.crt"
    rm -f "$TLS_DIR/server.csr" "$TLS_DIR/server.ext" "$TLS_DIR/findimob-root-ca.srl"
fi
