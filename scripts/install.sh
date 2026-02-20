#!/bin/bash

# Simple installer for proxy-shadow-keys

set -e

echo "Starting proxy-shadow-keys installation..."

if command -v pipx >/dev/null 2>&1; then
    echo "Found pipx, installing via pipx..."
    pipx install proxy-shadow-keys
elif command -v pip3 >/dev/null 2>&1; then
    echo "Found pip3, installing via pip3..."
    pip3 install --user proxy-shadow-keys
elif command -v pip >/dev/null 2>&1; then
    echo "Found pip, installing via pip..."
    pip install --user proxy-shadow-keys
else
    echo "Error: Neither pip nor pipx found. Please install Python and pip first."
    exit 1
fi

echo "Installation complete! Try running 'proxy-shadow-keys --help'"
