# MuleSoft AI Auditor 🛡️🤖
**Arquitectura:** RAG (Retrieval-Augmented Generation) empleando modelos locales con Ollama y bases vectoriales.

Este proyecto permite incorporar una base de conocimiento corporativa (en formato PDF) de la cual se generarán embeddings locales para, posteriormente, auditar código fuente de MuleSoft contrastándolo contra estas buenas prácticas utilizando un modelo de IA local en Ollama.

## 📂 Estructura del Proyecto
* `knowledge/`: Coloca aquí tus PDFs de Buenas Prácticas y Seguridad MuleSoft (ej. documentos de arquitectura).
* `projects/input/`: Coloca en esta carpeta subdirectorios con los repositorios de MuleSoft a auditar (analizará `.xml`, `.dwl`, `.yaml`, `.properties`).
* `projects/reports/`: Resultados en Markdown del análisis de deuda técnica y hallazgos generados por la Inteligencia Artificial.
* `scripts/`: Lógica de indexación RAG y ejecución de la auditoría construida en Python.
* `db/`: Base de datos vectorial persistente (ChromaDB) que guardará el modelo de conocimiento (persist_directory).

## 🚀 Requisitos y Configuración

1. **Modelos (Módulo Ollama):**
   * Asegúrate de tener instalado Ollama en tu equipo y funcionando.
   * Descarga el modelo local que usarán los scripts (para el Chat y para los Embeddings):
     ```bash
     ollama pull llama3.1
     ```
   * Asegúrate de que el servicio esté activo (generalmente usando la app de escritorio o ejecutando `ollama serve`).

2. **Entorno Python:**
   * Instala las dependencias y librerías modernas actualizadas en LangChain para Ollama y ChromaDB:
     ```bash
     pip install langchain langchain-community chromadb "unstructured[pdf]" lxml tiktoken langchain-chroma langchain-ollama langchain-core
     ```

## 🛠️ Pasos de Uso del Proyecto

### Fase 1: Creación de Embeddings e Ingesta de Datos (Indexar Documentos)
El primer paso constructivo es construir tu base de datos vectorial leyendo los PDFs corporativos.

1. Asegúrate de colocar tus archivos PDF dentro del directorio `knowledge/`.
2. Para procesarlos y poblar la base de datos, ejecuta el script de ingesta:
   ```bash
   python scripts/index_docs.py
   ```
3. **¿Qué ocurre internamente?** El script va a fragmentar el PDF (`RecursiveCharacterTextSplitter`), empleará la clase `OllamaEmbeddings(model="llama3.1")` de Langchain para vectorizar estos componentes de texto y los persistirá y guardará directamente en la carpeta local `/db`.

### Fase 2: Análisis Automatizado de Código y Auditoría RAG
Una vez consolidada la base del conocimiento documentado, el LLM inspeccionará el código fuente de los proyectos que desees verificar frente a esos hallazgos.

1. Copia y pega las carpetas enteras de los proyectos de MuleSoft a analizar dentro del pipeline ingresándolos a `projects/input/` (ej: `projects/input/mi-api-sys-sapi/`).
2. Dispara el agente auditor de código ejecutando:
   ```bash
   python scripts/audit_project.py
   ```
3. **¿Qué ocurre internamente?** El script identificará archivos relevantes esquivando dependencias compiladas (target, .mule, etc), usará la base en ChromaDB para recuperar `(k=3)` las normativas más afines que correspondan a esa porción de código, e insertará todo en un prompt inyectado usando la API de `ChatOllama(model="llama3.1", temperature=0)`.
## 🌐 Portal Web (Recomendado)
El proyecto ahora cuenta con un Interfaz Web premium y estético que elimina por completo la necesidad de usar la línea de comandos para las auditorías diarias.

### Inicio del Portal
1. Activa tu entorno virtual: `source venv/bin/activate`
2. Ejecuta el servidor desde la raíz del proyecto:
   ```bash
   python main.py
   ```
3. Abre tu navegador en: **http://localhost:8000**
4. **Login por defecto:** Usuario: `admin` | Contraseña: `admin`

### Características de la Interfaz:
- **Subida Fácil:** Comprime la carpeta de tu API o Proyecto MuleSoft en un archivo `.zip` y arrástralo directamente a la zona de carga de la web.
- **Base de Conocimiento Dinámica:** A través de la Pestaña "Nutrir IA", puedes subir PDFs con normativas nuevas que automáticamente re-entrenarán los vectores de la IA.
- **Pipeline RAG Automático:** El sistema lo depositará, extraerá en `projects/input/` y llamará directamente al Agente IA de evaluación.
- **Visualizador Integrado:** Una vez termine, puedes leer de manera dinámica y renderizada la matriz de hallazgos en la misma plataforma web.
