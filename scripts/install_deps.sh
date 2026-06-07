#!/usr/bin/env bash
# install_deps.sh - 一键装 chromium 系统依赖
# 适用: Debian/Ubuntu 容器 (apt)
set -e
echo "▶ 装 chromium 依赖 (apt)..."
apt-get update -qq
apt-get install -y --no-install-recommends \
  libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
  libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
  libxrandr2 libgbm1 libxss1 libasound2 fonts-noto-cjk \
  libgtk-3-0 libgconf-2-4 libxshmfence1
echo "▶ 装中文字体 (Noto CJK)..."
echo "✓ 依赖装好"
