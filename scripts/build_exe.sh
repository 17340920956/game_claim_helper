#!/bin/bash
set -e

# 检查是否安装了 pyinstaller
if ! command -v pyinstaller &> /dev/null
then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

echo "Building executable with PyInstaller..."
# 使用 spec 文件构建
pyinstaller game_claim_helper.spec

echo "Build completed. Executable is located in dist/game_claim_helper"
