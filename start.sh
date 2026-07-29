#!/bin/bash

echo "→ Starting Ollama..."
pkill ollama 2>/dev/null
ollama serve > /tmp/ollama.log 2>&1 &
sleep 2

echo "→ Starting backend + frontend on port 8000..."
cd backend
python main.py
