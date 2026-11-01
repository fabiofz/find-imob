#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
TLS_DIR="$PWD/.tls"
mkdir -p "$TLS_DIR"
chmod 700 "$TLS_DIR"

LAN_IP=""
if command -v powershell.exe >/dev/null 2>&1; then
    LAN_IP="$(powershell.exe -NoProfile -Command 'Get-NetIPAddress -InterfaceAlias "Wi-Fi" -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "169.254.*" } | Select-Object -First 1 -ExpandProperty IPAddress' 2>/dev/null | tr -d '\r' | head -n 1 || true)"
fi
if [[ ! "$LAN_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
    LAN_IP=""
fi

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

NEEDS_SERVER_CERT=0
if [[ ! -s "$TLS_DIR/server.key" || ! -s "$TLS_DIR/server.crt" ]] \
    || ! openssl x509 -in "$TLS_DIR/server.crt" -checkend 2592000 -noout >/dev/null 2>&1; then
    NEEDS_SERVER_CERT=1
fi
if [[ -n "$LAN_IP" ]] && ! openssl x509 -in "$TLS_DIR/server.crt" -noout -ext subjectAltName 2>/dev/null | grep -Fq "IP Address:$LAN_IP"; then
    NEEDS_SERVER_CERT=1
fi

if [[ "$NEEDS_SERVER_CERT" -eq 1 ]]; then
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out "$TLS_DIR/server.key"
    openssl req -new -key "$TLS_DIR/server.key" -out "$TLS_DIR/server.csr" \
        -subj "/CN=findimob.local"
    SERVER_SAN="DNS:findimob.local,DNS:localhost,IP:127.0.0.1"
    if [[ -n "$LAN_IP" ]]; then
        SERVER_SAN+=",IP:$LAN_IP"
    fi
    cat > "$TLS_DIR/server.ext" <<EXT
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=$SERVER_SAN
EXT
    openssl x509 -req -in "$TLS_DIR/server.csr" \
        -CA "$TLS_DIR/findimob-root-ca.crt" \
        -CAkey "$TLS_DIR/findimob-root-ca.key" \
        -CAcreateserial -out "$TLS_DIR/server.crt" \
        -days 397 -sha256 -extfile "$TLS_DIR/server.ext"
    chmod 600 "$TLS_DIR/server.key"
    chmod 644 "$TLS_DIR/server.crt"
    rm -f "$TLS_DIR/server.csr" "$TLS_DIR/server.ext" "$TLS_DIR/findimob-root-ca.srl"
    echo "Certificado Find Imob atualizado para LAN IP: ${LAN_IP:-nenhum}"
fi
