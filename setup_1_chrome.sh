#!/bin/bash
# ==============================================================================
# HyperFrames Setup — Part 1/3: Chrome
# ==============================================================================
# Downloads Chrome + all recursive deps, extracts them sequentially, and
# symlinks Chrome to an executable path (bypassing /opt noexec).
#
# Sandbox workarounds applied:
#   - apt-get download (not install) to avoid systemd postinst crashes
#   - Sequential dpkg -x to avoid overlay FS Bus errors
#   - Copy Chrome from /opt (noexec) to /usr/local
# ==============================================================================

set -euo pipefail

log() { echo ""; echo "=== $1 ==="; }

# --------------------------------------------------------------------------
# 1. Verify pre-installed tools
# --------------------------------------------------------------------------
log "1/3 Verifying pre-installed tools"
echo "Node.js: $(node -v)"
echo "npm:     $(npm -v)"
echo "FFmpeg:  $(ffmpeg -version 2>&1 | head -n 1)"

# --------------------------------------------------------------------------
# 2. Download Chrome + all recursive dependencies
# --------------------------------------------------------------------------
log "2/3 Downloading Chrome & dependencies"

if command -v google-chrome-stable >/dev/null 2>&1 && google-chrome-stable --version >/dev/null 2>&1; then
  echo "Chrome already installed: $(google-chrome-stable --version)"
else
  mkdir -p /workspace/debs
  cd /workspace/debs

  wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    -O /var/tmp/google-chrome.deb

  deps="ca-certificates fonts-liberation libasound2t64 libatk-bridge2.0-0t64 \
    libatk1.0-0t64 libatspi2.0-0t64 libc6 libcairo2 libcups2t64 libcurl4 \
    libdbus-1-3 libexpat1 libgbm1 libglib2.0-0 libgtk-3-0t64 libnspr4 libnss3 \
    libpango-1.0-0 libudev1 libvulkan1 libx11-6 libxcb1 libxcomposite1 \
    libxdamage1 libxext6 libxfixes3 libxkbcommon0 libxrandr2 wget xdg-utils"

  apt-get update -qq 2>/dev/null || true
  apt-cache depends --recurse --no-recommends --no-suggests \
    --no-conflicts --no-breaks --no-replaces --no-enhances $deps \
    | grep "^\w" | sort -u > /var/tmp/all_deps.txt

  echo "Downloading $(wc -l < /var/tmp/all_deps.txt) packages..."
  cat /var/tmp/all_deps.txt | xargs apt-get download 2>/dev/null || true

  # Extract packages sequentially (parallel causes Bus errors on overlay FS)
  log "Extracting packages (sequential)"
  for deb in /workspace/debs/*.deb; do
    [ -f "$deb" ] && dpkg -x "$deb" / 2>/dev/null || true
  done
  dpkg -x /var/tmp/google-chrome.deb / 2>/dev/null || true

  # Move Chrome from /opt (noexec) to /usr/local
  log "3/3 Setting up Chrome"
  cp -a /opt/google/chrome /usr/local/chrome
  ln -sf /usr/local/chrome/google-chrome /usr/bin/google-chrome-stable
  ln -sf /usr/local/chrome/google-chrome /usr/bin/google-chrome
  echo "Chrome: $(google-chrome-stable --version)"
fi

echo ""
echo "=== Part 1/3 Done ==="
