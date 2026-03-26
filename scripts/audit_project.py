import os
import sys
import subprocess
import re
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

    # 1. Prompt diseñado para Tablas de Acción
    template = """
    Eres un Arquitecto de Soluciones Senior. Tu misión es auditar el archivo '{file_name}' \
contrastándolo con las BUENAS PRÁCTICAS del contexto.

    CONTEXTO TÉCNICO:
    {context}

    CÓDIGO A EVALUAR:
    {question}

    REGLAS DE SALIDA — LEE CON ATENCIÓN ANTES DE RESPONDER:

    REGLA 1: Tu respuesta COMPLETA debe ser ÚNICAMENTE una tabla Markdown. NADA MÁS.
    REGLA 2: PROHIBIDO escribir texto antes o después de la tabla (introduciones, conclusiones, comentarios).
    REGLA 3: PROHIBIDO fusionar varias celdas en una sola línea. Cada fila DEBE ocupar su propia línea.
    REGLA 4: Cada fila DEBE seguir exactamente este formato (5 columnas separadas por |):
    | Alta | Seguridad | Descripción del hallazgo | `fragmento` | Acción concreta |
    REGLA 5: Si el archivo CUMPLE con todo, responde ÚNICAMENTE con el texto: ✅ CUMPLE

    FORMATO OBLIGATORIO DE LA TABLA:
    | Prioridad | Categoría | Hallazgo/Observación | Fragmento de Código | Acción Sugerida para el Dev |
    | :--- | :--- | :--- | :--- | :--- |
    | Alta | Seguridad | Ejemplo de hallazgo | `código aquí` | Acción concreta aquí |

    Columnas:
    - Prioridad: Alta | Media | Baja
    - Categoría: Seguridad | Performance | Estándar | Conectividad
    - Fragmento de Código: usa backticks inline. Si es largo, muestra solo la parte relevante.
    - Acción Sugerida: sé directo y técnico (ej: "Mover credencial a Secure Properties").
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
                        import json
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
                            count_alta += len(re.findall(r'\|\s*Alta\s*\|', result, re.IGNORECASE))
                            count_media += len(re.findall(r'\|\s*Media\s*\|', result, re.IGNORECASE))
                            count_baja += len(re.findall(r'\|\s*Baja\s*\|', result, re.IGNORECASE))
                            full_report += f"### 📄 Archivo: `{rel_path}`\n\n{result}\n\n"
                    except Exception as e:
                        print(f"  ❌ Error: {e}")

        # Guardar resultado consolidado
        status = "🟢 Saludable"
        if count_alta > 0:
            status = "🔴 Riesgo Crítico"
        elif count_media > 0:
            status = "🟡 Riesgo Medio"

        dashboard = f"""## 📊 Resumen Ejecutivo

<div style="display: flex; gap: 10px; margin-bottom: 20px;">
    <div style="flex: 1; background: rgba(255, 50, 50, 0.1); border: 1px solid rgba(255, 50, 50, 0.5); padding: 15px; border-radius: 8px; text-align: center;">
        <h3 style="margin: 0; color: #ff5555; font-size: 2em;">{count_alta}</h3>
        <span style="color: #ff5555; font-weight: bold;">Criticidad Alta</span>
    </div>
    <div style="flex: 1; background: rgba(255, 165, 0, 0.1); border: 1px solid rgba(255, 165, 0, 0.5); padding: 15px; border-radius: 8px; text-align: center;">
        <h3 style="margin: 0; color: #ffaa00; font-size: 2em;">{count_media}</h3>
        <span style="color: #ffaa00; font-weight: bold;">Criticidad Media</span>
    </div>
    <div style="flex: 1; background: rgba(0, 200, 0, 0.1); border: 1px solid rgba(0, 200, 0, 0.5); padding: 15px; border-radius: 8px; text-align: center;">
        <h3 style="margin: 0; color: #00cc00; font-size: 2em;">{count_baja}</h3>
        <span style="color: #00cc00; font-weight: bold;">Criticidad Baja</span>
    </div>
</div>

### 🎯 Estatus General del Proyecto
**Estado actual:** {status}

"""
        if count_alta > 0:
            dashboard += "El proyecto presenta **Riesgo Alto** debido a vulnerabilidades u observaciones críticas. Se requiere intervención y refactorización inmediata.\n\n"
        elif count_media > 0:
            dashboard += "El proyecto presenta **Riesgo Medio**. Se recomienda planificar refactorizaciones a corto plazo para evitar acumulación de deuda técnica.\n\n"
        else:
            dashboard += "El proyecto presenta **Riesgo Bajo/Saludable**. El código se encuentra alineado a las buenas prácticas.\n\n"

        dashboard += """### 📋 Tareas de Acciones Futuras
- [ ] 🔴 **Alta prioridad:** Revisar y corregir todos los hallazgos de "Criticidad Alta" antes del próximo pase a producción.
- [ ] 🟡 **Media prioridad:** Agendar sesiones de code-review para los hallazgos de "Criticidad Media".
- [ ] 🟢 **Mejora continua:** Planificar la corrección de los hallazgos de "Criticidad Baja" durante los tiempos de holgura.
- [ ] 🔁 **Validación:** Ejecutar el Auditor IA nuevamente después de aplicar correcciones corporativas.

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