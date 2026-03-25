import os
import sys
import subprocess
from langchain_community.document_loaders import DirectoryLoader, UnstructuredPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma  # Librería actualizada
from langchain_ollama import OllamaEmbeddings # Librería actualizada

# Configuración
KNOWLEDGE_DIR = "knowledge"
DB_DIR = "db"

def index_manuals():
    MODEL_NAME = sys.argv[1] if len(sys.argv) > 1 else "llama3.1"
    if not os.path.exists(KNOWLEDGE_DIR) or not os.listdir(KNOWLEDGE_DIR):
        print(f"❌ Error: La carpeta '{KNOWLEDGE_DIR}' está vacía. Pon tus PDFs ahí.")
        return

    print("🔍 Cargando manuales de buenas prácticas...")
    loader = DirectoryLoader(KNOWLEDGE_DIR, glob="./*.pdf", loader_cls=UnstructuredPDFLoader)
    docs = loader.load()
    
    # Dividimos el texto en fragmentos lógicos
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = text_splitter.split_documents(docs)
    
    print(f"✅ Se han generado {len(chunks)} fragmentos de conocimiento.")
    
    # Creamos la base de datos vectorial usando la nueva clase de Ollama
    EMBED_MODEL = "nomic-embed-text"
    print(f"🧠 Generando Embeddings con motor de alta velocidad ({EMBED_MODEL})...")
    try:
        print(f"🦙 Validando disponibilidad del motor de embeddings...")
        installed = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if EMBED_MODEL.lower() not in installed.stdout.lower():
            print(f"🔼 Motor '{EMBED_MODEL}' no encontrado. Descargando...")
            subprocess.run(["ollama", "pull", EMBED_MODEL])
        else:
            print(f"✅ Motor '{EMBED_MODEL}' ya disponible. Saltando descarga.")
        
        embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        
        vector_db = Chroma.from_documents(
            documents=chunks, 
            embedding=embeddings, 
            persist_directory=DB_DIR
        )
        print(f"✨ ¡Éxito! Base de datos creada con {len(chunks)} vectores.")
    except Exception as e:
        print(f"❌ Error al crear embeddings: {e}")
        print("Tip: Asegúrate de que 'ollama serve' esté corriendo y hayas hecho 'ollama pull llama3.1'")

if __name__ == "__main__":
    index_manuals()