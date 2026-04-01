#!/bin/bash
# Quick launcher for Lute v3
PORT="${1:-5001}"
uv run python devstart.py --port "$PORT"
