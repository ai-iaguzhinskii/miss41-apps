#!/bin/bash
cd "$(dirname "$0")"
pip install fastapi uvicorn httpx --quiet
uvicorn server:app --host 0.0.0.0 --port 8766 --reload
