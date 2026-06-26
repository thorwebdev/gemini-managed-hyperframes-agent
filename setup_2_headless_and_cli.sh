#!/bin/bash
# ==============================================================================
# HyperFrames Setup — Part 2/3: chrome-headless-shell + hyperframes CLI
# ==============================================================================
# Downloads chrome-headless-shell via curl (bypasses blocked Node.js DNS)
# and installs the hyperframes CLI with --ignore-scripts to avoid
# onnxruntime-node postinstall failures in the sandbox.
# ==============================================================================

set -euo pipefail

log() { echo ""; echo "=== $1 ==="; }

# --------------------------------------------------------------------------
# 1. Install chrome-headless-shell
#    Downloaded via curl (which uses the HTTP proxy correctly).
#    DO NOT use @puppeteer/browsers install — Node.js DNS is blocked.
# --------------------------------------------------------------------------
log "1/2 Installing chrome-headless-shell"

if command -v chrome-headless-shell >/dev/null 2>&1 && chrome-headless-shell --version >/dev/null 2>&1; then
  echo "chrome-headless-shell already installed: $(chrome-headless-shell --version)"
else
  CHROME_VERSION=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE)
  echo "Latest stable: $CHROME_VERSION"

  mkdir -p /var/tmp/chrome-hs-download
  cd /var/tmp/chrome-hs-download
  curl -sO "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-headless-shell-linux64.zip"
  unzip -qo chrome-headless-shell-linux64.zip

  mkdir -p /usr/local/chrome-headless-shell
  cp -r chrome-headless-shell-linux64/* /usr/local/chrome-headless-shell/
  ln -sf /usr/local/chrome-headless-shell/chrome-headless-shell /usr/bin/chrome-headless-shell
  echo "chrome-headless-shell: $(chrome-headless-shell --version)"
fi

# Set HYPERFRAMES_BROWSER_PATH so hyperframes uses the optimized headless shell.
# ~/.bashrc doesn't get sourced in sandbox command executions (each is a fresh
# non-login shell), so we persist via /etc/profile.d/ and /etc/environment.
export HYPERFRAMES_BROWSER_PATH=/usr/bin/chrome-headless-shell
echo 'export HYPERFRAMES_BROWSER_PATH=/usr/bin/chrome-headless-shell' > /etc/profile.d/hyperframes.sh 2>/dev/null || true
echo 'HYPERFRAMES_BROWSER_PATH=/usr/bin/chrome-headless-shell' >> /etc/environment 2>/dev/null || true
echo 'export HYPERFRAMES_BROWSER_PATH=/usr/bin/chrome-headless-shell' >> ~/.bashrc 2>/dev/null || true

# Bulletproof Workaround: Wrap the binaries system-wide since non-interactive shells
# do not read profile or rc files.
wrap_binary() {
  local name="$1"
  local binary_path
  binary_path=$(which "$name" 2>/dev/null)
  if [ -n "$binary_path" ] && [ ! -f "${binary_path}-real" ]; then
    echo "Creating environment-injected wrapper for $name at $binary_path"
    mv "$binary_path" "${binary_path}-real"
    cat << EOF > "$binary_path"
#!/bin/bash
export HYPERFRAMES_BROWSER_PATH=/usr/bin/chrome-headless-shell
exec "\$(dirname "\$0")/${name}-real" "\$@"
EOF
    chmod +x "$binary_path"
  fi
}

wrap_binary "npx"
wrap_binary "npm"

# --------------------------------------------------------------------------
# 2. Install hyperframes CLI
#    Uses --ignore-scripts to skip onnxruntime-node postinstall (which fails
#    because Node.js can't do DNS or direct TCP in this sandbox).
#    Then manually runs the postinstall with proxy vars.
# --------------------------------------------------------------------------
log "2/2 Installing hyperframes CLI"

export NODE_TLS_REJECT_UNAUTHORIZED=0

if command -v hyperframes >/dev/null 2>&1; then
  echo "hyperframes already installed: $(hyperframes --help 2>&1 | head -n 1)"
else
  npm install -g --ignore-scripts hyperframes

  # Manually run onnxruntime-node postinstall with proxy configured
  ONNX_DIR="/usr/lib/node_modules/hyperframes/node_modules/onnxruntime-node"
  if [ -d "$ONNX_DIR" ] && [ -f "$ONNX_DIR/script/install.js" ]; then
    echo "Running onnxruntime-node postinstall with proxy..."
    cd "$ONNX_DIR"
    GLOBAL_AGENT_HTTPS_PROXY="${HTTPS_PROXY:-${HTTP_PROXY:-}}" \
      GLOBAL_AGENT_HTTP_PROXY="${HTTP_PROXY:-}" \
      NODE_TLS_REJECT_UNAUTHORIZED=0 \
      node ./script/install 2>/dev/null || echo "  (onnxruntime-node install warning — non-fatal)"
  fi
fi

# Wrap the installed hyperframes CLI
wrap_binary "hyperframes"

echo "hyperframes wrapper verified: $(hyperframes --help 2>&1 | head -n 1)"

echo ""
echo "=== Part 2/3 Done ==="
