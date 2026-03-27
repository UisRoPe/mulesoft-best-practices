from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import shutil
import zipfile
import os
import sys
import subprocess
import glob
import asyncio
import json

# Use the same Python interpreter that's running this server
PYTHON = sys.executable

active_audit_process = None

app = FastAPI(title="Auditor IA Portal")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
os.makedirs("projects/input", exist_ok=True)
os.makedirs("projects/reports", exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("knowledge", exist_ok=True)
os.makedirs("db", exist_ok=True)

# Mount static files (will hold our frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("static/index.html", "r") as f:
        return f.read()

@app.post("/login")
async def login(request: Request):
    data = await request.json()
    if data.get("username") == "admin" and data.get("password") == "admin":
        return {"status": "success", "token": "dummy-jwt-token"}
    raise HTTPException(status_code=401, detail="Credenciales inválidas")

@app.get("/progress")
async def get_progress():
    progress_file = "projects/reports/.progress"
    if os.path.exists(progress_file):
        try:
            with open(progress_file, "r") as f:
                data = json.load(f)
            return data
        except Exception:
            pass
    return {"current": 0, "total": 0, "file": ""}

@app.get("/check_install")
async def check_install():
    if os.path.exists(".installed"):
        return {"installed": True}
    
    # Smart validation for existing users: check directories
    dirs_verify = ["knowledge", "db", "projects/input", "projects/reports"]
    dirs_exist = all(os.path.exists(d) for d in dirs_verify)
    
    # Smart validation for existing users: check ollama installation
    has_ollama = False
    try:
        if shutil.which("ollama"):
            has_ollama = True
    except Exception:
        pass
        
    if dirs_exist and has_ollama:
        # Create flag for future fast checks
        with open(".installed", "w") as f:
            f.write("installed")
        return {"installed": True}
        
    return {"installed": False}

@app.post("/install")
async def run_install():
    if os.path.exists(".installed"):
        return {"status": "success", "message": "Ya instalado"}
    try:
        os.chmod("setup.sh", 0o755)
        process = subprocess.run(
            ["./setup.sh"], 
            capture_output=True, 
            text=True
        )
        if process.returncode != 0:
            return {"status": "error", "logs": process.stderr}
            
        with open(".installed", "w") as f:
            f.write("installed")
            
        return {"status": "success", "logs": process.stdout}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante instalación: {str(e)}")

@app.post("/upload")
async def upload_project(model: str = Form(...), file: UploadFile = File(...)):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="El archivo no es un ZIP")

    input_dir = "projects/input"
    project_name = os.path.splitext(file.filename)[0]
    project_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).strip()
    if not project_name:
        project_name = "Proyecto_Desconocido"
        
    extract_dir = os.path.join(input_dir, project_name)
    os.makedirs(extract_dir, exist_ok=True)
    zip_path = os.path.join(input_dir, f"{project_name}.zip")
    
    # Read asynchronously then write to disk
    contents = await file.read()
    with open(zip_path, "wb") as buffer:
        buffer.write(contents)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        os.remove(zip_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al descomprimir: {str(e)}")

    progress_file = "projects/reports/.progress"
    try:
        os.makedirs("projects/reports", exist_ok=True)
        with open(progress_file, "w") as f:
            json.dump({"current": 0, "total": 0, "file": "Verificando/Descargando el modelo de IA local (Esto puede tomar minutos en el primer inicio)..."}, f)
    except:
        pass

    global active_audit_process
    try:
        active_audit_process = subprocess.Popen(
            [PYTHON, "scripts/audit_project.py", model, project_name]
        )
        # Wait without blocking the event loop
        loop = asyncio.get_running_loop()
        returncode = await loop.run_in_executor(None, active_audit_process.wait)
        active_audit_process = None
        if returncode != 0 and returncode != -15:
            return {"status": "error", "logs": "Falló la auditoría. Revisa los logs de la consola del servidor."}
        if returncode == -15:
            return {"status": "error", "logs": "Auditoría cancelada."}
    except Exception as e:
        active_audit_process = None
        raise HTTPException(status_code=500, detail=f"Error durante auditoría: {str(e)}")

    return {"status": "success", "logs": "Auditoría completada exitosamente."}

@app.get("/projects")
async def list_projects():
    input_dir = "projects/input"
    projects = [d for d in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, d))]
    return {"projects": sorted(projects)}

@app.delete("/projects/{project_name}")
async def delete_project(project_name: str):
    dir_path = os.path.join("projects/input", project_name)
    if os.path.isdir(dir_path):
        shutil.rmtree(dir_path)
        return {"status": "success", "message": "Proyecto eliminado."}
    raise HTTPException(status_code=404, detail="El proyecto no existe.")

@app.put("/projects/{project_name}")
async def rename_project(project_name: str, request: Request):
    data = await request.json()
    new_name = data.get("new_name")
    if not new_name:
        raise HTTPException(status_code=400, detail="Nuevo nombre es requerido")
        
    old_path = os.path.join("projects/input", project_name)
    new_path = os.path.join("projects/input", new_name)
    
    if not os.path.isdir(old_path):
        raise HTTPException(status_code=404, detail="El proyecto no existe.")
    if os.path.exists(new_path):
        raise HTTPException(status_code=400, detail="Ya existe un proyecto con ese nombre.")
        
    os.rename(old_path, new_path)
    return {"status": "success", "message": "Proyecto renombrado exitosamente."}

@app.post("/audit_existing")
async def audit_existing(model: str = Form(...), project_name: str = Form(...)):
    input_dir = "projects/input"
    if not os.path.isdir(os.path.join(input_dir, project_name)):
        raise HTTPException(status_code=404, detail="El proyecto no existe localmente.")
        
    progress_file = "projects/reports/.progress"
    try:
        os.makedirs("projects/reports", exist_ok=True)
        with open(progress_file, "w") as f:
            json.dump({"current": 0, "total": 0, "file": "Verificando/Descargando el modelo de IA local (Esto puede tomar minutos en el primer inicio)..."}, f)
    except:
        pass

    global active_audit_process
    try:
        active_audit_process = subprocess.Popen(
            [PYTHON, "scripts/audit_project.py", model, project_name]
        )
        loop = asyncio.get_running_loop()
        returncode = await loop.run_in_executor(None, active_audit_process.wait)
        active_audit_process = None
        if returncode != 0 and returncode != -15:
            return {"status": "error", "logs": "Falló la auditoría. Revisa los logs de la consola del servidor."}
        if returncode == -15:
            return {"status": "error", "logs": "Auditoría cancelada."}
    except Exception as e:
        active_audit_process = None
        raise HTTPException(status_code=500, detail=f"Error durante auditoría: {str(e)}")

    return {"status": "success", "logs": "Auditoría completada exitosamente."}

@app.post("/cancel_audit")
def cancel_audit():
    global active_audit_process
    if active_audit_process:
        active_audit_process.terminate()
        active_audit_process = None
        progress_file = "projects/reports/.progress"
        try:
            with open(progress_file, "w") as f:
                json.dump({"current": 0, "total": 0, "file": "✖️ Auditoría cancelada por el usuario."}, f)
        except:
            pass
        return {"status": "success"}
    return {"status": "error", "detail": "No hay un proceso activo."}

@app.post("/upload_knowledge")
async def upload_knowledge(model: str = Form(...), files: list[UploadFile] = File(...)):
    print("\n" + "="*80)
    print(f"📥 RECIBIENDO: /upload_knowledge (model={model}, archivos={len(files)})")
    print("="*80)
    
    # Validar que hay PDFs
    pdf_files_received = [f.filename for f in files if f.filename.endswith(".pdf")]
    print(f"✅ PDFs recibidos: {pdf_files_received}")
    
    if not pdf_files_received:
        print("❌ No hay PDFs en la solicitud")
        return {"status": "error", "logs": "No se recibieron archivos PDF"}
    
    # Limpiamos conocimientos anteriores y borramos la base de datos vectorial
    print(f"\n🗑️  Limpiando directorios anteriores...")
    if os.path.exists("knowledge"):
        shutil.rmtree("knowledge")
        print("   - Eliminado: knowledge/")
    if os.path.exists("db"):
        shutil.rmtree("db")
        print("   - Eliminado: db/")

    os.makedirs("knowledge", exist_ok=True)
    print("   - Creado: knowledge/")
    
    # Procesamos todos los archivos
    print(f"\n💾 Guardando PDFs...")
    saved_files = []
    for file in files:
        if not file.filename.endswith(".pdf"):
            print(f"   ⏭️  Skipped (no es PDF): {file.filename}")
            continue
        
        pdf_path = os.path.join("knowledge", file.filename)
        file_size = 0
        with open(pdf_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                buffer.write(chunk)
                file_size += len(chunk)
        
        saved_files.append(pdf_path)
        print(f"   ✅ Guardado: {file.filename} ({file_size / 1024:.1f} KB)")

    print(f"\n✅ Total guardado: {len(saved_files)} PDF(s)")
    
    # Ejecutar indexación
    print(f"\n🚀 Iniciando indexación con: python scripts/index_docs.py {model}")
    try:
        process = subprocess.run(
            [PYTHON, "scripts/index_docs.py", model],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Mostrar output
        print(f"\n--- SALIDA DEL SCRIPT ---")
        if process.stdout:
            for line in process.stdout.split('\n')[-20:]:  # Últimas 20 líneas
                if line.strip():
                    print(f"{line}")
        
        if process.stderr:
            print(f"\n--- ERRORES ---")
            print(process.stderr)
        
        print(f"\n--- RESULTADO: Return Code {process.returncode} ---\n")
        
        if process.returncode != 0:
            error_msg = process.stderr or process.stdout or "Falló sin mensaje de error"
            print(f"❌ INDEXACIÓN FALLÓ")
            return {"status": "error", "logs": error_msg}
        
        print(f"✅ INDEXACIÓN EXITOSA")
        
    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT: Indexación >300 segundos")
        return {"status": "error", "logs": "Indexación tardó demasiado (>5 min). ¿Está ollama corriendo?"}
    except Exception as e:
        print(f"❌ ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"Error durante re-indexación vectorial: {str(e)}")

    print("="*80 + "\n")
    return {"status": "success", "logs": "Indexación exitosa.", "message": "Base de datos vectorizada actualizada."}

@app.get("/reports")
async def list_reports(response: JSONResponse):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    reports_dir = "projects/reports"
    files = glob.glob(os.path.join(reports_dir, "*.md"))
    report_names = [os.path.basename(f) for f in files]
    return {"reports": sorted(report_names, reverse=True)}

@app.get("/reports/{report_name}")
async def get_report(report_name: str):
    report_path = os.path.join("projects/reports", report_name)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return {"content": content}

@app.delete("/reports/{report_name}")
async def delete_report(report_name: str):
    report_path = os.path.join("projects/reports", report_name)
    if os.path.exists(report_path):
        os.remove(report_path)
        return {"status": "success", "message": "Reporte eliminado."}
    raise HTTPException(status_code=404, detail="Reporte no encontrado")

@app.put("/reports/{report_name}")
async def rename_report(report_name: str, request: Request):
    data = await request.json()
    new_name = data.get("new_name")
    if not new_name:
        raise HTTPException(status_code=400, detail="Nuevo nombre es requerido")
        
    if not new_name.endswith(".md"):
        new_name += ".md"
        
    old_path = os.path.join("projects/reports", report_name)
    new_path = os.path.join("projects/reports", new_name)
    
    if not os.path.exists(old_path):
        raise HTTPException(status_code=404, detail="El reporte no existe.")
    if os.path.exists(new_path):
        raise HTTPException(status_code=400, detail="Ya existe un reporte con ese nombre.")
        
    os.rename(old_path, new_path)
    return {"status": "success", "message": "Reporte renombrado exitosamente."}

@app.get("/download/{report_name}")
async def download_report(report_name: str):
    report_path = os.path.join("projects/reports", report_name)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return FileResponse(path=report_path, filename=report_name, media_type='text/markdown')

# ─── Checklist de Reglas ──────────────────────────────────────────────────────

@app.get("/rules")
async def get_rules():
    """Retorna todos los fragmentos de conocimiento almacenados en ChromaDB."""
    if not os.path.exists("db"):
        return {"rules": [], "error": "No hay base de conocimiento indexada. Sube PDFs en 'Nutrir IA' primero."}
    
    try:
        import chromadb
        
        # Usar ruta absoluta para asegurar que ChromaDB la encuentra
        db_path = os.path.abspath("db")
        client = chromadb.PersistentClient(path=db_path)
        collections = client.list_collections()
        
        if not collections:
            return {"rules": [], "error": "La base de conocimiento está vacía. Los chunks no se generaron correctamente."}
        
        # Usar la primera colección (usualmente "documents")
        collection = collections[0]
        result = collection.get(include=["documents", "metadatas"])
        
        documents = result.get("documents") or []
        ids       = result.get("ids")       or []
        metadatas = result.get("metadatas") or []
        
        if not documents:
            return {"rules": [], "error": "La base de conocimiento está vacía (sin documentos)."}
        
        print(f"✅ Se cargaron {len(documents)} documentos desde ChromaDB")

        rules = []
        for i, doc in enumerate(documents):
            if not doc or not doc.strip():
                continue
            
            source = ""
            try:
                meta = metadatas[i] if metadatas and i < len(metadatas) else {}
                raw  = (meta or {}).get("source", "")
                source = os.path.basename(raw) if raw else ""
            except Exception:
                pass
            
            rules.append({
                "id":     ids[i] if i < len(ids) else str(i),
                "text":   doc.strip(),
                "source": source,
            })
        
        return {"rules": rules, "total": len(rules)}
    except Exception as e:
        print(f"❌ Error en /rules: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"rules": [], "error": f"Error cargando base de conocimiento: {str(e)}"}


@app.get("/rules/checklist")
async def get_checklist():
    """Carga el estado guardado del checklist."""
    checklist_path = "projects/reports/checklist.json"
    if os.path.exists(checklist_path):
        with open(checklist_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"selections": {}}


@app.post("/rules/checklist")
async def save_checklist(request: Request):
    """Persiste el estado del checklist (selections + texts de reglas)."""
    data = await request.json()
    checklist_path = "projects/reports/checklist.json"
    os.makedirs("projects/reports", exist_ok=True)
    with open(checklist_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {"status": "success", "message": "Checklist guardado correctamente."}


@app.post("/generate_final_doc")
async def generate_final_doc_endpoint(model: str = Form(...), report_name: str = Form(...)):
    """Genera un Documento Final de Gobernanza a partir del checklist + reporte de auditoría."""
    report_path = os.path.join("projects/reports", report_name)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Reporte de auditoría no encontrado.")

    checklist_path = "projects/reports/checklist.json"
    if not os.path.exists(checklist_path):
        raise HTTPException(
            status_code=400,
            detail="No hay checklist guardado. Ve a la pestaña 'Checklist', clasifica las reglas y guarda la selección.",
        )

    try:
        process = subprocess.run(
            [PYTHON, "scripts/generate_final_doc.py", model, report_name],
            capture_output=True, text=True,
        )
        if process.returncode != 0:
            return {"status": "error", "logs": process.stderr or "Error al generar el documento final."}

        final_doc_name = report_name.replace("Matriz_Hallazgos_", "Documento_Final_")
        if not final_doc_name.startswith("Documento_Final_"):
            final_doc_name = "Documento_Final_" + report_name

        return {"status": "success", "document": final_doc_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
