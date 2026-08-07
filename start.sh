#!/bin/bash

echo "→ Starting Ollama..."
pkill ollama 2>/dev/null
ollama serve > /tmp/ollama.log 2>&1 &
sleep 3

echo "→ Pulling tinyllama model (if needed)..."
ollama pull tinyllama

echo "→ Starting backend + frontend on port 8000..."
python main.py