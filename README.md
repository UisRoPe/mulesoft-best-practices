# Auditor IA 🛡️🤖

**Plataforma de Auditoría RAG** con diseño *Industrial Cyberpunk* impulsada por Inteligencia Artificial Local (Ollama) y Bases de Datos Vectoriales.

Este proyecto permite ingerir manuales corporativos (PDFs), vectorizarlos utilizando un motor universal ultrarrápido, y emplear modelos híbridos (Llama 3.1, Qwen 2.5, etc.) para auditar código fuente de proyectos MuleSoft, contrastándolos arquitectónicamente en tiempo real.

---

## ⚡️ Características Premium
- **Diseño Cyberpunk Brutalista:** Interfaz de usuario inmersiva con overlay de monitores CRT de seguridad, botones mecánicos animados y una mini-consola hacker en tiempo real.
- **Arquitectura RAG Desacoplada:** El sistema separa matemáticamente los Embeddings del modelo de Chat. Utiliza `nomic-embed-text` para construir la base de conocimiento ChromaDB, permitiéndote auditar el mismo proyecto turnando entre cualquier modelo de IA instantáneamente sin romper los vectores.
- **Multihilo "Non-Blocking" (Subprocesos):** FastAPI envía las auditorías masivas a su *ThreadPoolExecutor*. Esto libera la aplicación web para pintar los logs en la interfaz gráfica archivo-por-archivo en tiempo real.
- **Frenado de Emergencia (SIGTERM):** Un botón 🛑 en el visor permite liquidar limpiamente el análisis de la IA en pleno vuelo sin corromper la memoria del servidor.
- **Protección de Contexto:** Protección nativa contra el "Context Length Exceeded" que trunca archivos monstruosamente largos (como `application-types.xml`) para modelos ligeros (1B).

---

## 🚀 Instalación y Despliegue en 1 Clic

Con la versión actual, **ya no necesitas usar la consola.** El portal web se encarga de todo.

1. Abre una terminal y colócate dentro de este repositorio.
2. Inicia el servidor maestro:
   ```bash
   bash start.sh
   # (Si prefieres uso manual: source venv/bin/activate && python main.py)
   ```
3. Dirígete a **http://localhost:8000**
4. Credenciales de acceso:
   * **Usuario:** `admin`
   * **Password:** `admin`

*(Durante tu primer inicio de sesión, el sistema descargará el motor base y preparará el entorno visualmente).*

---

## 🛠️ Flujo de Operación (Portal Web)

### 1. Seleccionar la IA (Sidebar)
Puedes elegir libremente la *"inteligencia"* temporal que operará:
- **Llama 3.1 (8B):** Para auditorías pesadas corporativas.
- **Llama 3.2 (1B)** / **Qwen 2.5 (1.5B):** Modelos Edge ultrarrápidos para laptops, ideales para revisión de sintaxis y deuda técnica estándar.
*(Si no tienes el modelo, el backend lo descargará bajo-demanda silenciosamente; verás el progreso de descarga en la consola).*

### 2. Nutrir IA (Conocimiento Básico)
1. Sube tus PDFs (Manuales de Seguridad, Arquitectura) en la pestaña **Nutrir IA**.
2. El sistema creará un índice usando `nomic-embed-text`. Esto borra el índice anterior y asegura compatibilidad con cualquier modelo chat que escojas en el paso 1.

### 3. Auditar Código
1. En la pestaña **Nuevo Análisis**, arrastra un archivo `.zip` directo de Anypoint Studio. 
2. Observa la consola renderizar los descubrimientos en vivo.
3. Puedes **Pausar/Detener** la revisión desde la misma ventana.
4. Explora todos los proyectos resguardados desde **Repositorios**, donde puedes editarlos, borrarlos y volverlos a auditar con otro modelo en paralelo.

### 4. Reportes en Vivo
Ve a la pestaña **Reportes** para leer la Matriz Markdown generada final. El visor de código ocupará todo el ancho para una fácil lectura técnica y permite un botón de descarga global.

---

> **Estructura Interna del Repositorio:**
> `db/` (ChromaDB), `projects/` (Entorno estéril para zips e informes), `knowledge/` (PDFs crudos), `static/` (Arquitectura Frontend CSS+JS V2.2), `scripts/` (Núcleo Vectorial). *Las herramientas de IDE y agentes están ocultas por .gitignore.*
