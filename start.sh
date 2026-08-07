#!/bin/bash

echo "→ Starting Ollama..."
pkill ollama 2>/dev/null
ollama serve > /tmp/ollama.log 2>&1 &
sleep 5

echo "→ Pulling tinyllama (if needed)..."
ollama pull tinyllama

echo "→ Starting the app..."
python main.py