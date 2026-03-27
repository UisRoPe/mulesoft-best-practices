#!/usr/bin/env python3
"""Genera tareas desde el reporte de auditoría Markdown."""
import os
import sys
import json

REPORTS_DIR = "projects/reports"


def generate_tasks():
    """Extrae tareas del reporte y genera JSON."""
    
    if len(sys.argv) < 2:
        print("❌ USO: python generate_tasks.py <report_name>", file=sys.stderr)
        sys.exit(1)
    
    report_name = sys.argv[1]
    report_path = os.path.join(REPORTS_DIR, report_name)
    
    if not os.path.exists(report_path):
        print(f"❌ Reporte no encontrado: {report_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Leer reporte
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Extraer tareas
        tasks = extract_tasks(content)
        
        if not tasks:
            print("⚠️  No se encontraron tareas, usando ejemplos...", file=sys.stderr)
            tasks = generate_example_tasks()
        
        # Generar nombre de proyecto
        project_name = report_name.replace("Matriz_Hallazgos_", "").replace(".md", "")
        
        # Crear JSON
        output_data = {
            "project": project_name,
            "total_tasks": len(tasks),
            "tasks": tasks
        }
        
        # Guardar JSON
        json_filename = f"Tareas_{project_name}.json"
        json_path = os.path.join(REPORTS_DIR, json_filename)
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ JSON guardado: {json_filename}")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


def extract_tasks(content):
    """Extrae tareas de las tablas Markdown."""
    tasks = []
    task_id = 1
    
    lines = content.split('\n')
    in_table = False
    
    for line in lines:
        # Detectar tabla
        if '| # |' in line or '| Severidad' in line:
            in_table = True
            continue
        
        if in_table and line.strip().startswith('|') and '---' not in line:
            parts = [p.strip() for p in line.split('|')]
            parts = [p for p in parts if p]
            
            if len(parts) >= 6:
                try:
                    num = parts[0]
                    if not num.isdigit():
                        continue
                    
                    severidad = parts[1]
                    categoria = parts[2]
                    hallazgo = parts[3]
                    codigo = parts[4]
                    accion = parts[5]
                    
                    # Mapear severidad
                    prioridad = "Media"
                    if "Alta" in severidad:
                        prioridad = "Alta"
                    elif "Baja" in severidad:
                        prioridad = "Baja"
                    
                    task = {
                        "id": f"TP-{task_id:03d}",
                        "prioridad": prioridad,
                        "categoria": categoria,
                        "hallazgo": hallazgo,
                        "archivo": codigo if "src" in codigo else "N/A",
                        "accion": accion,
                        "tiempo": "2h" if prioridad == "Alta" else ("1h" if prioridad == "Media" else "30m"),
                        "aplica": False
                    }
                    
                    tasks.append(task)
                    task_id += 1
                except (IndexError, ValueError):
                    pass
        
        if in_table and not line.strip():
            in_table = False
    
    return tasks


def generate_example_tasks():
    """Tareas de ejemplo."""
    return [
        {
            "id": "TP-001",
            "prioridad": "Alta",
            "categoria": "Seguridad",
            "hallazgo": "Revisar configuración de HTTPS",
            "archivo": "src/main/resources/application.xml",
            "accion": "Ajustar puerto y certificados SSL",
            "tiempo": "2h",
            "aplica": False
        },
        {
            "id": "TP-002",
            "prioridad": "Media",
            "categoria": "Documentación",
            "hallazgo": "Agregar comentarios a validadores",
            "archivo": "src/main/mule/common/commons.xml",
            "accion": "Documentar componentes validation:is-true",
            "tiempo": "1h",
            "aplica": False
        }
    ]


if __name__ == "__main__":
    generate_tasks()
