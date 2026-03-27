import os
import sys
import json
import subprocess
import re
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

REPORTS_DIR = "projects/reports"


def extract_tasks_from_report(report_content):
    """Extrae tareas directamente del reporte de auditoría parseando las tablas."""
    tasks = []
    task_counter = 1
    
    # Buscar todas las tablas de hallazgos con patrón: | # | Severidad | Categoría | Hallazgo | ...
    # Patrón más flexible para tablas Markdown
    lines = report_content.split('\n')
    in_table = False
    table_rows = []
    
    for line in lines:
        if '| # |' in line or ('|' in line and 'Severidad' in line):
            in_table = True
            continue
        
        if in_table and line.strip().startswith('|') and line.count('|') >= 6:
            # Esto es una fila de datos
            table_rows.append(line)
        elif in_table and (not line.strip().startswith('|') or line.count('|') < 5):
            in_table = False
    
    # Parsear filas
    for row in table_rows:
        parts = [p.strip() for p in row.split('|')[1:-1]]  # Quitar primera y última columna vacías
        
        if len(parts) >= 6:
            try:
                num = parts[0]
                severidad = parts[1]
                categoria = parts[2]
                hallazgo = parts[3]
                codigo = parts[4]
                accion = parts[5]
                
                # Mapear severidad a prioridad
                prioridad_map = {'🔴 Alta': 'Alta', '🟡 Media': 'Media', '🟢 Baja': 'Baja'}
                prioridad = prioridad_map.get(severidad.strip(), 'Media')
                
                task_id = f"TP-{task_counter:03d}"
                
                tasks.append({
                    'id': task_id,
                    'prioridad': prioridad,
                    'hallazgo': hallazgo,
                    'archivo': codigo if codigo and 'src' in codigo else 'N/A',
                    'accion': accion,
                    'tiempo': '2h' if prioridad == 'Alta' else '1h',
                    'status': '☐',
                    'aplica': False
                })
                
                task_counter += 1
            except:
                pass
    
    return tasks if tasks else _generate_ai_tasks(report_content)


def _generate_ai_tasks(report_content):
    """Fallback: Genera tareas con IA si no se puede parsear el reporte."""
    print("⚠️  No se pudieron parsear tareas, generando con IA...")
    
    llm = ChatOllama(model="llama3.1", temperature=0, num_predict=2000, num_ctx=8192)
    
    template = """Analiza este reporte de auditoría MuleSoft y extrae EXACTAMENTE 5 tareas en formato JSON.

REPORTE:
{audit_report}

Responde ÚNICAMENTE con JSON válido, sin texto adicional:
{{
  "tasks": [
    {{"id": "TP-001", "prioridad": "Alta", "hallazgo": "Descripción corta", "archivo": "ruta/archivo.xml", "accion": "Pasos", "tiempo": "2h"}},
    {{"id": "TP-002", "prioridad": "Media", "hallazgo": "Descripción", "archivo": "ruta/archivo.xml", "accion": "Pasos", "tiempo": "1h"}}
  ]
}}"""

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    
    try:
        result = chain.invoke({"audit_report": report_content[:4000]})
        data = json.loads(result)
        tasks = []
        for t in data.get('tasks', []):
            t['aplica'] = False
            tasks.append(t)
        return tasks
    except:
        # Fallback total: crear tareas dummy
        return [{
            'id': 'TP-001',
            'prioridad': 'Alta',
            'hallazgo': 'Revisar configuración de seguridad',
            'archivo': 'src/main/resources/application.xml',
            'accion': 'Actualizar propiedades',
            'tiempo': '2h',
            'status': '☐',
            'aplica': False
        }]


def generate_tasks():
    MODEL_NAME = sys.argv[1] if len(sys.argv) > 1 else "llama3.1"
    REPORT_NAME = sys.argv[2] if len(sys.argv) > 2 else None

    if not REPORT_NAME:
        print("❌ Se requiere el nombre del reporte como segundo argumento.")
        sys.exit(1)

    # ── Cargar reporte de auditoría ───────────────────────────────────────────
    report_path = os.path.join(REPORTS_DIR, REPORT_NAME)
    if not os.path.exists(report_path):
        print(f"❌ Reporte no encontrado: {report_path}")
        sys.exit(1)

    with open(report_path, "r", encoding="utf-8") as f:
        report_content = f.read()

    print("📊 Extrayendo tareas del reporte...")
    tasks_list = extract_tasks_from_report(report_content)

    # ── Guardar como JSON ──────────────────────────────────────────────────────
    project_name = REPORT_NAME.replace("Matriz_Hallazgos_", "").replace(".md", "")
    tasks_json_filename = f"Tareas_{project_name}.json"
    tasks_json_path = os.path.join(REPORTS_DIR, tasks_json_filename)
    
    with open(tasks_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "filename": f"Tareas_{project_name}.md",
            "project": project_name,
            "tasks": tasks_list
        }, f, ensure_ascii=False, indent=2)

    print(f"✨ Tareas exportadas: {tasks_json_path}")
    print(f"📊 Total de tareas: {len(tasks_list)}")


if __name__ == "__main__":
    generate_tasks()

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

