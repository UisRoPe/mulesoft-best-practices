# Auditor IA 🛡️🤖

**Plataforma de Auditoría RAG** con diseño *Industrial Cyberpunk* impulsada por Inteligencia Artificial Local (Ollama) y Bases de Datos Vectoriales.

Este proyecto permite ingerir manuales corporativos (PDFs), vectorizarlos utilizando un motor universal ultrarrápido, y emplear modelos híbridos (Llama 3.1, Qwen 2.5, etc.) para auditar código fuente de proyectos MuleSoft, contrastándolos arquitectónicamente en tiempo real.

---

## ⚡️ Características
- **Diseño Cyberpunk Interactivo:** Interfaz inmersiva con controles en tiempo real
- **Arquitectura RAG Desacoplada:** Separación matemática de Embeddings y modelos de Chat
  - Embeddings: `nomic-embed-text` con ChromaDB
  - Auditoría con modelos intercambiables (Llama 3.1, Qwen 2.5, etc.)
- **Multihilo No-Bloqueante:** FastAPI con ThreadPoolExecutor para análisis en tiempo real
- **Frenado de Emergencia:** Detener análisis en progreso sin corromper memoria
- **Protección de Contexto:** Truncamiento inteligente para modelos ligeros

---

## 🚀 Inicio Rápido

### 1. Primer Arranque
```bash
bash start.sh
```
El script detectará si necesita dependencias y las instalará automáticamente.

### 2. Acceder al Portal
- **URL:** http://localhost:8000
- **Usuario:** `admin`
- **Contraseña:** `admin`

### 3. Flujo de Operación

#### 📚 Nutrir IA (Conocimiento Base)
1. Ve a la pestaña **Nutrir IA**
2. Sube tus PDFs (Manuales, Arquitectura, Políticas)
3. El sistema crea un índice vectorial automáticamente

#### 🔍 Auditar Código
1. En **Nuevo Análisis**, carga un proyecto MuleSoft (`.zip`)
2. Observa los descubrimientos en vivo en la consola
3. Pausa o detén el análisis cuando lo necesites

#### 📊 Ver Reportes
1. Accede a **Reportes**
2. Examina la Matriz de Hallazgos en Markdown
3. Descarga el reporte completo

---

## 🗂️ Estructura del Proyecto

```
.
├── main.py                 # FastAPI - Servidor principal
├── start.sh               # Script de arranque
├── setup.sh               # Configuración de dependencias
├── static/                # Frontend (HTML, CSS, JS)
├── scripts/               # Core de auditoría
│   ├── audit_project.py   # Lógica de auditoría
│   ├── index_docs.py      # Indexación vectorial
│   └── generate_final_doc.py  # Generación de reportes
├── projects/              # Workspace
│   ├── input/            # Proyectos subidos
│   └── reports/          # Reportes generados
├── knowledge/            # PDFs ingestionados
├── db/                   # ChromaDB (vectores)
└── venv/                 # Ambiente virtual
```

---

## 📋 Requisitos Previos

- **Python 3.9+**
- **Ollama** instalado localmente (para modelos de IA)
- **~5GB** de espacio disponible (para modelos y base de datos)

---

## 🔧 Desarrollo Manual

Si prefieres controlar el proceso manualmente:

```bash
# 1. Activar ambiente virtual
source venv/bin/activate

# 2. Instalar dependencias (si es necesario)
pip install -r requirements.txt

# 3. Ejecutar servidor
python main.py
```

---

## 🎯 Modelos Disponibles

| Modelo | Tamaño | Velocidad | Uso Recomendado |
|--------|--------|-----------|-----------------|
| **Llama 3.1** | 8B | Moderada | Auditorías profundas corporativas |
| **Qwen 2.5** | 1.5B | Muy Rápida | Revisiones ágiles, laptops |
| **Llama 3.2** | 1B | Muy Rápida | Edge computing, análisis sintáctico |

> Los modelos se descargan automáticamente bajo demanda si no están disponibles localmente.

---

## 🛑 Controles de Emergencia

- **Pausar Auditoría:** Click en el botón ⏸️ de la consola
- **Detener Auditoría:** Click en el botón 🛑 de la consola
- **Limpiar Índice:** Sube nuevos PDFs para regenerar

---

## 📝 Notas Técnicas

- **ChromaDB**: Base de datos vectorial persistente en `db/`
- **Ollama**: Gestiona modelos LLM localmente
- **FastAPI**: Framework web asincrónico
- **ThreadPoolExecutor**: Procesa auditorías sin bloquear UI

---

## 🤝 Soporte

Para reportar problemas o sugerencias, crea un issue en el repositorio.

---

**Versión:** 2.0 | **Última actualización:** Marzo 2026
