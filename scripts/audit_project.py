import os
import sys
import subprocess
import re
import json
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Configuración de rutas
DB_DIR = "db"
PROJECTS_ROOT = "projects/input"
REPORTS_DIR = "projects/reports"

def run_audit():
    MODEL_NAME = sys.argv[1] if len(sys.argv) > 1 else "llama3.1"
    EMBED_MODEL = "nomic-embed-text"
    print(f"🚀 Generando Matriz... usando modelo: {MODEL_NAME}")
    
    print(f"🦙 Validando disponibilidad de modelos locales...")
    
    # Verificar si el modelo de chat ya está descargado
    installed = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    installed_models = installed.stdout.lower()
    
    if MODEL_NAME.lower() not in installed_models:
        print(f"🔼 Modelo '{MODEL_NAME}' no encontrado. Descargando...")
        subprocess.run(["ollama", "pull", MODEL_NAME])
    else:
        print(f"✅ Modelo '{MODEL_NAME}' ya disponible. Saltando descarga.")
    
    if EMBED_MODEL.lower() not in installed_models:
        print(f"🔼 Motor de embeddings '{EMBED_MODEL}' no encontrado. Descargando...")
        subprocess.run(["ollama", "pull", EMBED_MODEL])
    else:
        print(f"✅ Motor '{EMBED_MODEL}' ya disponible. Saltando descarga.")
    
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    if not os.path.exists(DB_DIR):
        print("❌ Error: Corre primero index_docs.py")
        return
        
    vector_db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    retriever = vector_db.as_retriever(search_kwargs={"k": 3})
    # Expandimos num_ctx a 8192 (aprox 8k tokens) para permitir archivos más largos sin quebrar el modelo
    llm = ChatOllama(model=MODEL_NAME, temperature=0, num_predict=1500, num_ctx=8192)

    # Prompt profesional con formato estándar de auditoría
    template = """Eres un Arquitecto de Soluciones Senior especializado en MuleSoft e integración empresarial.
Tu tarea es realizar una revisión técnica formal del archivo `{file_name}` aplicando los estándares corporativos del CONTEXTO.

---
ESTÁNDARES DE REFERENCIA (base de conocimiento corporativa):
{context}

---
ARTEFACTO A REVISAR — `{file_name}`:
{question}

---
INSTRUCCIONES DE RESPUESTA — OBLIGATORIO CUMPLIR AL PIE DE LA LETRA:

1. Si el archivo cumple con todos los estándares aplicables, responde ÚNICAMENTE con esta línea:
   ✅ CUMPLE — Sin observaciones para `{file_name}`.

2. Si existen observaciones, responde ÚNICAMENTE con la tabla Markdown siguiente, sin ningún texto antes ni después:

| # | Severidad | Categoría | Hallazgo | Fragmento de Código | Acción Recomendada | Esfuerzo |
| :---: | :---: | :--- | :--- | :--- | :--- | :---: |
| 1 | 🔴 Alta | Seguridad | Descripción clara y específica del problema encontrado | `fragmento relevante` | Acción concreta y técnica | Alto |

DEFINICIONES DE COLUMNAS:
- **#**: Número secuencial del hallazgo (1, 2, 3…).
- **Severidad**: 🔴 Alta (riesgo en producción / seguridad) | 🟡 Media (deuda técnica importante) | 🟢 Baja (mejora de calidad).
- **Categoría**: Seguridad | Manejo de Errores | Rendimiento | Estándares de Nomenclatura | Logging | Configuración | Conectividad | Documentación.
- **Hallazgo**: Descripción técnica precisa. Referencia el estándar incumplido si aplica.
- **Fragmento de Código**: Usa backticks inline con el fragmento exacto que origina el hallazgo. Máximo 80 caracteres.
- **Acción Recomendada**: Instrucción técnica directa y accionable (ej: "Externalizar a `secure::db.password` en Secure Properties Store").
- **Esfuerzo**: Alto | Medio | Bajo.

RESTRICCIONES ABSOLUTAS:
- PROHIBIDO agregar encabezados, introducción, conclusión o comentarios fuera de la tabla.
- PROHIBIDO combinar múltiples hallazgos en una sola fila.
- PROHIBIDO generar filas vacías o con datos de ejemplo.
- Cada fila DEBE ocupar exactamente una línea en el Markdown.
"""
    prompt = ChatPromptTemplate.from_template(template)

    chain = (
        {
            "context": (lambda x: f"Reglas de desarrollo, buenas prácticas de arquitectura y seguridad aplicables a {x['file_name']}") | retriever, 
            "question": lambda x: x["question"],
            "file_name": lambda x: x["file_name"]
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    projects = [d for d in os.listdir(PROJECTS_ROOT) if os.path.isdir(os.path.join(PROJECTS_ROOT, d))]
    TARGET_PROJECT = sys.argv[2] if len(sys.argv) > 2 else None
    
    if TARGET_PROJECT:
        if TARGET_PROJECT in projects:
            projects = [TARGET_PROJECT]
        else:
            print(f"❌ Proyecto seleccionado '{TARGET_PROJECT}' no se encontró en {PROJECTS_ROOT}")
            return
    
    # Pre-calcular el total de archivos a escanear
    total_files = 0
    for project_name in projects:
        project_path = os.path.join(PROJECTS_ROOT, project_name)
        for root, _, files in os.walk(project_path):
            if any(x in root for x in ["target", ".mule", "bin", ".settings", "src/test"]): continue
            for file in files:
                if file.endswith(('.xml', '.dwl', '.yaml', '.properties')):
                    total_files += 1

    current_file = 0

    for project_name in projects:
        print(f"📁 Analizando Proyecto: {project_name}")
        count_alta = 0
        count_media = 0
        count_baja = 0
        full_report = f"# 🛡️ Reporte de Deuda Técnica: {project_name}\n\n"
        full_report += "Este reporte contiene los hallazgos detectados por IA basados en los manuales de seguridad y desarrollo corporativos.\n\n"
        
        project_path = os.path.join(PROJECTS_ROOT, project_name)

        for root, _, files in os.walk(project_path):
            # Ignoramos carpetas que no son de código fuente productivo para limpiar el reporte
            if any(x in root for x in ["target", ".mule", "bin", ".settings", "src/test"]): continue
            
            for file in files:
                if file.endswith(('.xml', '.dwl', '.yaml', '.properties')):
                    current_file += 1
                    rel_path = os.path.relpath(os.path.join(root, file), project_path)
                    print(f"  🔍 {rel_path}...")

                    # Reportar progreso global
                    try:
                        os.makedirs(REPORTS_DIR, exist_ok=True)
                        with open(os.path.join(REPORTS_DIR, ".progress"), "w") as f_prog:
                            json.dump({"current": current_file, "total": total_files, "file": rel_path}, f_prog)
                    except Exception:
                        pass
                    
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        if not content.strip() or file == "application-types.xml" or file == "log4j2.xml": 
                            continue

                        # Límite de seguridad: Modelos pequeños (1B/3B) tienen ventanas de contexto limitadas.
                        # Con num_ctx=8192, tenemos espacio para la base de conocimientos y el código.
                        # 14,000 caracteres aseguran que nos mantengamos por debajo de ~4k-5k tokens.
                        if len(content) > 14000:
                            content = content[:14000] + "\n\n...[ADVERTENCIA: ARCHIVO TRUNCADO. MUY VOLUMINOSO.]..."

                        result = chain.invoke({"question": content, "file_name": rel_path})
                        
                        # Solo añadimos al reporte si hay algo que corregir
                        if "✅" not in result:
                            # Regex robusto: busca en filas de datos (empiezan con | número |)
                            count_alta  += len(re.findall(r'^\|[^|]*\d+[^|]*\|[^|]*Alta[^|]*\|',  result, re.IGNORECASE | re.MULTILINE))
                            count_media += len(re.findall(r'^\|[^|]*\d+[^|]*\|[^|]*Media[^|]*\|', result, re.IGNORECASE | re.MULTILINE))
                            count_baja  += len(re.findall(r'^\|[^|]*\d+[^|]*\|[^|]*Baja[^|]*\|',  result, re.IGNORECASE | re.MULTILINE))
                            full_report += f"### 📄 Archivo: `{rel_path}`\n\n{result}\n\n"
                    except Exception as e:
                        print(f"  ❌ Error: {e}")

        # Guardar resultado consolidado
        status = "🟢 Saludable"
        if count_alta > 0:
            status = "🔴 Riesgo Crítico"
        elif count_media > 0:
            status = "🟡 Riesgo Medio"

        total_hallazgos = count_alta + count_media + count_baja

        dashboard = f"""## 📊 Resumen Ejecutivo

| Indicador | Valor |
| :--- | :--- |
| **Proyecto auditado** | `{project_name}` |
| **Total de hallazgos** | **{total_hallazgos}** |
| 🔴 Severidad Alta | **{count_alta}** hallazgo{"s" if count_alta != 1 else ""} |
| 🟡 Severidad Media | **{count_media}** hallazgo{"s" if count_media != 1 else ""} |
| 🟢 Severidad Baja | **{count_baja}** hallazgo{"s" if count_baja != 1 else ""} |
| **Estatus general** | {status} |

"""
        if count_alta > 0:
            dashboard += "> ⚠️ **Riesgo Crítico** — El proyecto presenta vulnerabilidades de alta severidad que requieren atención inmediata antes del próximo pase a producción.\n\n"
        elif count_media > 0:
            dashboard += "> 🔶 **Riesgo Medio** — Se recomienda planificar sesiones de refactorización a corto plazo para evitar acumulación de deuda técnica.\n\n"
        else:
            dashboard += "> ✅ **Saludable** — El código está alineado con las buenas prácticas corporativas.\n\n"

        dashboard += f"""### 📋 Plan de Acción

| Prioridad | Tarea | Responsable |
| :---: | :--- | :--- |
| 🔴 Alta | Corregir los **{count_alta}** hallazgo{"s" if count_alta != 1 else ""} de severidad Alta antes del próximo release | Dev / Arquitecto |
| 🟡 Media | Agendar code-review para los **{count_media}** hallazgo{"s" if count_media != 1 else ""} de severidad Media | Dev Lead |
| 🟢 Baja | Planificar corrección de los **{count_baja}** hallazgo{"s" if count_baja != 1 else ""} de severidad Baja en tiempos de holgura | Dev |
| 🔁 Validación | Re-ejecutar Auditor IA tras aplicar correcciones | QA / Arquitecto |

---

"""
        full_report = full_report.replace("desarrollo corporativos.\n\n", "desarrollo corporativos.\n\n" + dashboard)

        os.makedirs(REPORTS_DIR, exist_ok=True)
        out_path = os.path.join(REPORTS_DIR, f"Matriz_Hallazgos_{project_name}.md")
        with open(out_path, "w") as f:
            f.write(full_report)
        print(f"\n✨ ¡Listo! Matriz generada en: {out_path}")

if __name__ == "__main__":
    run_audit()