from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import shutil
import zipfile
import os
import subprocess
import glob
import glob
import asyncio

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
            import json
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

    import json
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
            ["python", "scripts/audit_project.py", model, project_name]
        )
        # Wait without blocking the event loop
        loop = asyncio.get_event_loop()
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
        import shutil
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
        
    import json
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
            ["python", "scripts/audit_project.py", model, project_name]
        )
        loop = asyncio.get_event_loop()
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
        import json
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
    # Limpiamos conocimientos anteriores y borramos la base de datos vectorial
    if os.path.exists("knowledge"):
        shutil.rmtree("knowledge")
    if os.path.exists("db"):
        shutil.rmtree("db")

    os.makedirs("knowledge", exist_ok=True)
    
    # Procesamos todos los archivos
    for file in files:
        if not file.filename.endswith(".pdf"):
            continue
        pdf_path = os.path.join("knowledge", file.filename)
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    try:
        process = subprocess.run(
            ["python", "scripts/index_docs.py", model]
        )
        if process.returncode != 0:
            return {"status": "error", "logs": "Falló la indexación. Revisa los logs de la consola."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante re-indexación vectorial: {str(e)}")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
