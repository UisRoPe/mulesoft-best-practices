import os
import sys
import json
import subprocess
import re
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

REPORTS_DIR = "projects/reports"


def parse_tasks_from_markdown(content):
    """Extrae tareas de la estructura Markdown generada."""
    tasks = []
    task_id_counter = 1
    
    # Buscar filas de tabla Markdown con formato: | ID | Hallazgo | ...
    table_pattern = r'\|\s*([TP\-\d]+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*([☐✓]+)\s*\|'
    matches = re.finditer(table_pattern, content, re.MULTILINE)
    
    for match in matches:
        task_id = match.group(1).strip()
        hallazgo = match.group(2).strip()
        archivo = match.group(3).strip()
        accion = match.group(4).strip()
        tiempo = match.group(5).strip()
        status = match.group(6).strip()
        
        tasks.append({
            'id': task_id,
            'hallazgo': hallazgo,
            'archivo': archivo,
            'accion': accion,
            'tiempo': tiempo,
            'status': status,
            'aplica': False  # Por defecto sin seleccionar
        })
    
    return tasks


def generate_tasks():
    MODEL_NAME = sys.argv[1] if len(sys.argv) > 1 else "llama3.1"
    REPORT_NAME = sys.argv[2] if len(sys.argv) > 2 else None

    if not REPORT_NAME:
        print("❌ Se requiere el nombre del reporte como segundo argumento.")
        sys.exit(1)

    # ── Verificar / descargar modelo ─────────────────────────────────────────
    installed = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    if MODEL_NAME.lower() not in installed.stdout.lower():
        print(f"🔼 Modelo '{MODEL_NAME}' no encontrado. Descargando...")
        subprocess.run(["ollama", "pull", MODEL_NAME])
    else:
        print(f"✅ Modelo '{MODEL_NAME}' disponible.")

    # ── Cargar reporte de auditoría ───────────────────────────────────────────
    report_path = os.path.join(REPORTS_DIR, REPORT_NAME)
    if not os.path.exists(report_path):
        print(f"❌ Reporte no encontrado: {report_path}")
        sys.exit(1)

    with open(report_path, "r", encoding="utf-8") as f:
        report_content = f.read()

    # Truncar para caber en ventana de contexto
    if len(report_content) > 8000:
        report_content = report_content[:8000] + "\n\n...[REPORTE TRUNCADO POR LONGITUD]..."

    # ── Invocar LLM para generar tareas ───────────────────────────────────────
    print(f"🚀 Generando tareas con '{MODEL_NAME}'...")
    llm = ChatOllama(model=MODEL_NAME, temperature=0, num_predict=3000, num_ctx=8192)

    template = """Eres un Project Manager especializado en MuleSoft. Tu tarea es convertir los hallazgos de auditoría en tareas concretas y accionables para los desarrolladores.

REPORTE DE AUDITORÍA:
{audit_report}

GENERA UN DOCUMENTO MARKDOWN CON LAS SIGUIENTES SECCIONES:

## 📋 Plan de Tareas — Auditoría Técnica

### 🔴 Tareas de Alta Prioridad (Bloqueantes)
Para cada hallazgo 🔴 Alta, crea una tabla con:
| ID | Hallazgo | Archivo | Acción | Tiempo Est. | Status |
| :---: | :--- | :--- | :--- | :---: | :---: |
| TP-001 | Descripción exacta | ruta/archivo.ext | Paso a paso (1, 2, 3...) | 2h | ☐ |

### 🟡 Tareas de Media Prioridad 
Para cada hallazgo 🟡 Media, sigue el mismo formato.

### 🟢 Tareas de Baja Prioridad
Para cada hallazgo 🟢 Baja, sigue el mismo formato.

### ✅ Criterios de Aceptación
Para cada tarea, define claramente qué significa "hecho":
- Unit tests pasando
- Code review aprobado
- Documentación actualizada
- Demostración en QA

### 📅 Timeline Sugerido
Estima sprints / personas / fechas.

### 👥 Asignación Sugerida
Por rol: Backend, Frontend, DevOps, QA.

INSTRUCCIONES CRÍTICAS:
- Sé ESPECÍFICO: ej "Cambiar la clase SecurityValidator.java línea 42"
- Sé ACCIONABLE: incluye comandos, URLs, herramientas
- Agrupa por severidad (Alta > Media > Baja)
- Cada tarea debe tener un ID único (TP-###)
- Incluye referencias directas a las rutas de archivo del reporte
- Si un hallazgo se repite en múltiples archivos, agrúpalos en una sola tarea
"""

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()

    result = chain.invoke({
        "audit_report": report_content,
    })

    # ── Guardar tareas en Markdown ──────────────────────────────────────────
    project_name = REPORT_NAME.replace("Matriz_Hallazgos_", "").replace(".md", "")
    tasks_filename = f"Tareas_{project_name}.md"
    tasks_path = os.path.join(REPORTS_DIR, tasks_filename)

    header = f"""# 📋 Plan de Tareas de Desarrollo — {project_name}

> Generado automáticamente por **Auditor IA** para acelerar el proceso de remediación

**Instrucciones para el equipo de desarrollo:**
1. Revisa todas las tareas asignadas a tu rol
2. Completa los pasos numerados en orden
3. Marca el checkbox ☐ → ☑️ al finalizar
4. Realiza un commit con el ID de la tarea (ej: git commit -m "TP-001: Fix XYZ")
5. Abre un PR con referencia a esta tarea

---

"""
    with open(tasks_path, "w", encoding="utf-8") as f:
        f.write(header + result)

    print(f"\n✨ Markdown generado: {tasks_path}")

    # ── Parsear y guardar como JSON ────────────────────────────────────────
    tasks_json_filename = f"Tareas_{project_name}.json"
    tasks_json_path = os.path.join(REPORTS_DIR, tasks_json_filename)
    
    tasks_list = parse_tasks_from_markdown(result)
    
    with open(tasks_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "filename": tasks_filename,
            "project": project_name,
            "tasks": tasks_list
        }, f, ensure_ascii=False, indent=2)

    print(f"📄 JSON generado: {tasks_json_path}")
    print(f"📊 Total de tareas: {len(tasks_list)}")


if __name__ == "__main__":
    generate_tasks()

