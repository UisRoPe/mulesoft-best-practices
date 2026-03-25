from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import shutil
import zipfile
import os
import subprocess
import glob

app = FastAPI(title="MuleSoft AI Auditor Portal")

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
    
    # Smart validation for existing users: check ollama llama3.1 model
    has_model = False
    try:
        if shutil.which("ollama"):
            proc = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            if proc.returncode == 0 and "llama3.1" in proc.stdout:
                has_model = True
    except Exception:
        pass
        
    if dirs_exist and has_model:
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
async def upload_project(file: UploadFile = File(...)):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="El archivo no es un ZIP")

    # Clear previous inputs to avoid rescanning old things
    input_dir = "projects/input"
    for item in os.listdir(input_dir):
        item_path = os.path.join(input_dir, item)
        if os.path.isfile(item_path) or os.path.islink(item_path):
            os.unlink(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)

    zip_path = os.path.join(input_dir, "uploaded_project.zip")
    
    # Save uploaded ZIP
    with open(zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract ZIP
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(input_dir)
        os.remove(zip_path) # Clean up ZIP after extraction
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al descomprimir: {str(e)}")

    import json
    progress_file = "projects/reports/.progress"
    try:
        os.makedirs("projects/reports", exist_ok=True)
        with open(progress_file, "w") as f:
            json.dump({"current": 0, "total": 0, "file": "Descomprimiendo archivos..."}, f)
    except:
        pass

    # Start the scan process synchronously (for simplicity in UI pulling)
    # This could take a while in a real scenario, but we handle it in frontend with a loading state.
    try:
        # We don't capture_output so the user can see live progress in their terminal
        process = subprocess.run(
            ["python", "scripts/audit_project.py"]
        )
        if process.returncode != 0:
            return {"status": "error", "logs": "Falló la auditoría. Revisa los logs de la consola."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante auditoría: {str(e)}")

    return {"status": "success", "logs": "Auditoría completada exitosamente."}

@app.post("/upload_knowledge")
async def upload_knowledge(files: list[UploadFile] = File(...)):
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
            ["python", "scripts/index_docs.py"]
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

@app.get("/download/{report_name}")
async def download_report(report_name: str):
    report_path = os.path.join("projects/reports", report_name)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return FileResponse(path=report_path, filename=report_name, media_type='text/markdown')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
