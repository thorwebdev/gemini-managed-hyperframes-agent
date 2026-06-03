#!/bin/bash
# ==============================================================================
# HyperFrames Setup — Part 3/3: Skills, GSAP, Cleanup & Verification
# ==============================================================================
# Installs HyperFrames skills, pre-downloads GSAP for offline headless Chrome
# use, cleans up temp files, and runs final verification.
# ==============================================================================

set -euo pipefail

log() { echo ""; echo "=== $1 ==="; }

export NODE_TLS_REJECT_UNAUTHORIZED=0
# Explicitly set BROWSER_PATH since each sandbox command is a fresh shell
export HYPERFRAMES_BROWSER_PATH=/usr/bin/chrome-headless-shell

# --------------------------------------------------------------------------
# 1. Install skills
#    npx fails due to noexec on cache dir, so install skills CLI globally first.
# --------------------------------------------------------------------------
log "1/3 Installing HyperFrames skills"

if [ -d "/.agents/skills/hyperframes" ]; then
  echo "Skills already installed at /.agents/skills/"
else
  # Install skills CLI globally (npx would fail due to noexec)
  npm install -g skills 2>/dev/null || true

  cd /workspace
  TMPDIR=/var/tmp NODE_TLS_REJECT_UNAUTHORIZED=0 \
    skills add heygen-com/hyperframes -y 2>/dev/null || true

  # Move skills to expected root location
  if [ -d "/workspace/.agents/skills" ]; then
    mkdir -p /.agents/skills/
    mv /workspace/.agents/skills/* /.agents/skills/ 2>/dev/null || true
    rm -rf /workspace/.agents/skills
  fi

  echo "Installed $(ls /.agents/skills/ 2>/dev/null | wc -l) skills"
fi

# --------------------------------------------------------------------------
# 2. Pre-download GSAP for offline use
#    Headless Chrome rejects CDN TLS certs (mitmproxy), so compositions
#    must load GSAP from a local file, not from cdn.jsdelivr.net.
# --------------------------------------------------------------------------
log "2/3 Pre-downloading GSAP"

mkdir -p /workspace/.cache/libs
if [ -f "/workspace/.cache/libs/gsap.min.js" ]; then
  echo "GSAP already downloaded"
else
  curl -sk -o /workspace/.cache/libs/gsap.min.js \
    https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js
  echo "GSAP: $(wc -c < /workspace/.cache/libs/gsap.min.js) bytes"
fi

# --------------------------------------------------------------------------
# 3. Cleanup temp files
# --------------------------------------------------------------------------
log "3/3 Cleanup"
rm -rf /workspace/debs /var/tmp/google-chrome.deb /var/tmp/chrome-hs-download \
  /var/tmp/all_deps.txt 2>/dev/null || true

# --------------------------------------------------------------------------
# Final verification
# --------------------------------------------------------------------------
log "SETUP COMPLETE — Verification"
echo "  FFmpeg:               $(ffmpeg -version 2>&1 | head -n 1)"
echo "  Chrome:               $(google-chrome-stable --version 2>&1)"
echo "  Chrome Headless Shell: $(chrome-headless-shell --version 2>&1)"
echo "  Hyperframes:          $(hyperframes --help 2>&1 | head -n 1)"
echo "  GSAP local:           /workspace/.cache/libs/gsap.min.js ($(wc -c < /workspace/.cache/libs/gsap.min.js 2>/dev/null || echo '0') bytes)"
echo "  Skills:               $(ls /.agents/skills/ 2>/dev/null | wc -l) installed"
echo "  BROWSER_PATH:         ${HYPERFRAMES_BROWSER_PATH:-NOT SET}"
echo ""
