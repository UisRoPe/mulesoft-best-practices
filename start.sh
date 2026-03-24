#!/bin/bash
# start.sh - Script de arranque Todo-en-Uno

echo "=========================================================="
echo "🚀 Iniciando MuleSoft AI Auditor..."
echo "=========================================================="

# 1. Corre la configuración y validación inteligente siempre
# Esto instalará todo automáticamente en máquinas totalmente nuevas
bash setup.sh

if [ $? -ne 0 ]; then
    echo "❌ Hubo un fallo en la instalación."
    exit 1
fi

# 2. Activar el entorno con las dependencias instaladas
source venv/bin/activate

# 3. Levantar el portal
echo "=========================================================="
echo "🌐 Levantando el portal Web..."
echo "👉 Abre tu navegador en: http://localhost:8000"
echo "👉 (Presiona Ctrl+C en esta terminal para apagarlo)"
echo "=========================================================="
python main.py
