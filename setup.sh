#!/bin/bash
# setup.sh - Script de configuración inicial para MuleSoft AI Auditor

echo "🛡️  Iniciando validación del sistema..."

# 1. Crear directorios base si no existen
mkdir -p knowledge projects/input projects/reports db
touch knowledge/.gitkeep projects/input/.gitkeep projects/reports/.gitkeep db/.gitkeep

# 2. Verificar si Python3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 no está instalado. Por favor, instálalo antes de continuar."
    exit 1
fi

# 3. Crear el entorno virtual (venv) si no existe
if [ ! -d "venv" ]; then
    echo "🐍 Creando el entorno virtual (venv)..."
    python3 -m venv venv
fi

# 4. Activar el entorno virtual para este script
source venv/bin/activate

# 5. Proceso core de instalación (Se salta si ya se hizo antes gracias a .installed)
if [ ! -f ".installed" ]; then
    echo "📦 Instalando las dependencias en Python vía pip..."
    pip install --upgrade pip
    pip install langchain langchain-community chromadb "unstructured[pdf]" lxml tiktoken langchain-chroma langchain-ollama langchain-core fastapi uvicorn python-multipart aiofiles

    echo "🦙 Verificando instalación de Ollama..."
    if ! command -v ollama &> /dev/null; then
        echo "⚠️  ATENCIÓN: 'ollama' no está instalado en el sistema."
        echo "Intentando instalar Ollama automáticamente..."
        if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
            curl -fsSL https://ollama.com/install.sh | sh
        else
            echo "❌ No pudimos instalar Ollama automáticamente en tu SO."
            echo "👉 Descárgalo versión desktop desde: https://ollama.com/download"
            exit 1
        fi
    fi

    echo "✅ Ollama detectado. Verificando y preparando entorno..."

    touch .installed
    echo "✨ ¡Componentes descargados e instalados exitosamente! ✨"
else
    echo "✅ Todas las dependencias e IA ya se encontraban instaladas."
fi
