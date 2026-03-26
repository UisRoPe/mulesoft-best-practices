import os
import sys
import json
import subprocess
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

REPORTS_DIR = "projects/reports"


def generate_final_doc():
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

    # ── Cargar checklist ──────────────────────────────────────────────────────
    checklist_path = os.path.join(REPORTS_DIR, "checklist.json")
    if not os.path.exists(checklist_path):
        print("❌ No se encontró checklist.json. Guarda primero el checklist.")
        sys.exit(1)

    with open(checklist_path, "r", encoding="utf-8") as f:
        checklist_data = json.load(f)

    selections = checklist_data.get("selections", {})
    rules_text = checklist_data.get("rules_text", {})

    applies = [rules_text[rid] for rid, status in selections.items() if status == "applies" and rid in rules_text]
    not_applies = [rules_text[rid] for rid, status in selections.items() if status == "not_applies" and rid in rules_text]

    print(f"📋 Reglas APLICAN: {len(applies)} | NO APLICAN: {len(not_applies)}")

    # ── Cargar reporte de auditoría ───────────────────────────────────────────
    report_path = os.path.join(REPORTS_DIR, REPORT_NAME)
    with open(report_path, "r", encoding="utf-8") as f:
        report_content = f.read()

    # Truncar para caber en ventana de contexto
    if len(report_content) > 8000:
        report_content = report_content[:8000] + "\n\n...[REPORTE TRUNCADO POR LONGITUD]..."

    applicable_block = "\n\n---\n\n".join(applies[:15])
    if len(applicable_block) > 4000:
        applicable_block = applicable_block[:4000] + "\n\n...[REGLAS TRUNCADAS]..."

    not_applicable_block = "\n".join(f"- {t[:120]}..." for t in not_applies[:10])

    # ── Invocar LLM ───────────────────────────────────────────────────────────
    print(f"🚀 Generando Documento Final con '{MODEL_NAME}'...")
    llm = ChatOllama(model=MODEL_NAME, temperature=0, num_predict=2500, num_ctx=8192)

    template = """Eres un Arquitecto de Soluciones Senior encargado de redactar un DOCUMENTO OFICIAL DE GOBERNANZA para un proyecto de integración MuleSoft.

REGLAS / ESTÁNDARES QUE APLICAN A ESTE PROYECTO:
{applicable_rules}

ESTÁNDARES QUE NO APLICAN (excluidos del alcance):
{not_applicable_rules}

HALLAZGOS DEL ANÁLISIS DE AUDITORÍA:
{audit_report}

INSTRUCCIONES ESTRICTAS:
Genera un documento Markdown profesional con las siguientes secciones EXACTAS:

## 1. Resumen Ejecutivo
Estado general de cumplimiento del proyecto vs los estándares aplicables.

## 2. Estándares Aplicados al Proyecto
Lista numerada de los estándares que aplican, con breve descripción.

## 3. Estándares Excluidos del Alcance
Lista de estándares que no aplican y justificación breve.

## 4. Hallazgos Críticos y Plan de Acción
Tabla Markdown con: | Prioridad | Hallazgo | Estándar Incumplido | Acción Requerida | Responsable |

## 5. Criterios de Aceptación para Pase a Producción
Lista de verificación (checkboxes Markdown) de lo que debe cumplirse antes del siguiente release.

## 6. Historial de Revisiones
Tabla de versiones del documento.

El tono debe ser formal, técnico y orientado a la acción. No incluyas texto fuera de estas secciones.
"""

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()

    result = chain.invoke({
        "applicable_rules": applicable_block if applicable_block else "No se seleccionaron reglas aplicables.",
        "not_applicable_rules": not_applicable_block if not_applicable_block else "Ninguno excluido.",
        "audit_report": report_content,
    })

    # ── Guardar documento final ───────────────────────────────────────────────
    project_name = REPORT_NAME.replace("Matriz_Hallazgos_", "").replace(".md", "")
    final_doc_name = f"Documento_Final_{project_name}.md"
    final_doc_path = os.path.join(REPORTS_DIR, final_doc_name)

    header = f"""# 📋 Documento Final de Gobernanza — {project_name}

> Generado por **Auditor IA** | Reglas aplicables: {len(applies)} | Excluidas: {len(not_applies)}

---

"""
    with open(final_doc_path, "w", encoding="utf-8") as f:
        f.write(header + result)

    print(f"\n✨ Documento Final generado: {final_doc_path}")


if __name__ == "__main__":
    generate_final_doc()
