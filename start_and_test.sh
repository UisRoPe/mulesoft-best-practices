#!/bin/bash
# Script para iniciar todo y hacer diagnóstico

set -e

cd "$(dirname "$0")"

echo ""
echo "======================================================================"
echo "🚀 INICIANDO AUDITOR IA + DIAGNÓSTICO"
echo "======================================================================"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "main.py" ]; then
    echo "❌ Error: No se encuentra main.py"
    echo "   Asegúrate de estar en el directorio correcto"
    exit 1
fi

# Activar venv si existe
if [ -d "venv" ]; then
    echo "1️⃣  Activando ambiente virtual..."
    source venv/bin/activate
    echo "   ✅ Activado"
else
    echo "⚠️  No hay venv, usando Python del sistema"
fi

echo ""
echo "2️⃣  Iniciando servidor FastAPI..."
echo "   Puerto: http://localhost:8000"
echo "   Para detener: Ctrl+C"
echo ""

# Iniciar servidor en background
python main.py &
SERVER_PID=$!

# Dar tiempo al servidor para iniciar
sleep 3

echo ""
echo "3️⃣  Ejecutando diagnóstico..."
sleep 1

# Ejecutar test
python test_api.py

# Mantener el servidor corriendo
echo ""
echo "======================================================================"
echo "✅ SERVIDOR CORRIENDO"
echo "======================================================================"
echo ""
echo "🌐 Accede a: http://localhost:8000"
echo "   Usuario: admin"
echo "   Contraseña: admin"
echo ""
echo "📝 Pasos:"
echo "   1. Inicia sesión"
echo "   2. Ve a 'Nutrir IA'"
echo "   3. Sube un PDF"
echo "   4. Verifica los logs en esta terminal"
echo ""

# Esperar a que el usuario presione Ctrl+C
wait $SERVER_PID
