#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
export SETUP_KEY="${SETUP_KEY:-Zorven-Setup-2026-Alpha-7f9d2c1e-Q7R9xM2k}"
python3 zorven/server.py
