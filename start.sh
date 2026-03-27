#!/bin/bash
# start.sh - Script de arranque del Auditor IA

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=========================================================="
echo "🚀 Iniciando Auditor IA RAG"
echo "=========================================================="
echo ""

# 1. Ejecutar setup para garantizar dependencias
if [ ! -d "venv" ] || [ ! -f ".installed" ]; then
    echo "📦 Preparando ambiente..."
    bash setup.sh
    if [ $? -ne 0 ]; then
        echo "❌ Error en la instalación"
        exit 1
    fi
fi

# 2. Activar entorno virtual
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 3. Iniciar servidor
echo ""
echo "=========================================================="
echo "🌐 Portal Web:"
echo "   URL: http://localhost:8000"
echo "   Usuario: admin"
echo "   Contraseña: admin"
echo ""
echo "   (Presiona Ctrl+C para detener)"
echo "=========================================================="
echo ""

python main.py
