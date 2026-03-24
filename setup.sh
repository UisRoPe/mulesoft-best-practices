#!/bin/bash

# setup.sh - Script de configuración inicial para MuleSoft AI Auditor

echo "🛡️  Iniciando configuración de MuleSoft AI Auditor..."

# 1. Crear directorios base si no existen (Git a menudo omite carpetas vacías)
echo "📁 Verificando estructura de directorios..."
mkdir -p knowledge
mkdir -p projects/input
mkdir -p projects/reports
mkdir -p db

# 2. Verificar si Python e pip están instalados
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python3 no está instalado."
    echo "Por favor, instala Python3 antes de continuar."
    exit 1
fi

# 3. Recomendación y creación de entorno virtual (Opcional pero recomendado)
echo "🐍 Creando el entorno virtual (venv)..."
python3 -m venv venv
source venv/bin/activate

# 4. Instalación de dependencias de IA y procesamiento
echo "📦 Instalando las dependencias en Python vía pip..."
pip install --upgrade pip
pip install langchain langchain-community chromadb "unstructured[pdf]" lxml tiktoken langchain-chroma langchain-ollama langchain-core fastapi uvicorn python-multipart aiofiles

# 5. Verificar e instalar modelo local Ollama
echo "🦙 Verificando instalación de Ollama..."
if ! command -v ollama &> /dev/null; then
    echo "⚠️  ATENCIÓN: La herramienta 'ollama' no está instalada en el sistema."
    echo "👉 Debes descargarla e instalarla manualmente desde: https://ollama.com/download"
    echo "👉 Una vez instalada, asegúrate de correr: ollama pull llama3.1"
else
    echo "✅ Ollama detectado. Verificando o descargando el modelo llama3.1..."
    echo "(Esto puede tardar dependiendo de tu conexión a internet si es la primera vez)"
    ollama pull llama3.1
fi

echo "=========================================================="
echo "✨ ¡Configuración completada exitosamente! ✨"
echo ""
echo "Recuerda que para ejecutar los scripts debes activar primero"
echo "tu entorno virtual en tu terminal ejecutando:"
echo "👉 source venv/bin/activate"
echo "=========================================================="

touch .installed
