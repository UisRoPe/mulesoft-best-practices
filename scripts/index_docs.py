#!/usr/bin/env python3
"""
Script mejorado para indexar PDFs en ChromaDB
"""
import os
import sys
import subprocess
from pathlib import Path

print(f"\n{'='*70}")
print(f"🚀 Iniciando indexación de PDFs")
print(f"{'='*70}\n")

# Configuración
KNOWLEDGE_DIR = "knowledge"
DB_DIR = "db"

# 1. Validar que tenemos PDFs
print(f"1️⃣  Buscando PDFs en {KNOWLEDGE_DIR}/...")
pdf_files = list(Path(KNOWLEDGE_DIR).glob("*.pdf"))

if not pdf_files:
    print(f"❌ No se encontraron archivos PDF en '{KNOWLEDGE_DIR}/'")
    print(f"   Archivos encontrados:")
    for item in os.listdir(KNOWLEDGE_DIR) if os.path.exists(KNOWLEDGE_DIR) else []:
        print(f"   - {item}")
    sys.exit(1)

print(f"✅ Se encontraron {len(pdf_files)} PDF(s)")
for pdf in pdf_files:
    print(f"   - {pdf.name} ({pdf.stat().st_size / 1024:.1f} KB)")
print()

# 2. Cargar PDFs
print(f"2️⃣  Cargando contenido de PDFs...")
try:
    from langchain_community.document_loaders import UnstructuredPDFLoader
    from langchain_core.documents import Document
    import pypdf
    
    docs = []
    
    for pdf_path in pdf_files:
        print(f"\n   📄 {pdf_path.name}")
        
        # Intentar con UnstructuredPDFLoader (mejor para textos complejos)
        try:
            print(f"      → Intentando con Unstructured...")
            loader = UnstructuredPDFLoader(str(pdf_path))
            loaded_docs = loader.load()
            if loaded_docs:
                docs.extend(loaded_docs)
                print(f"      ✅ Cargado ({len(loaded_docs)} fragmentos)")
                continue
        except Exception as e:
            print(f"      ⚠️  Unstructured fallió: {type(e).__name__}")
        
        # Fallback a pypdf
        try:
            print(f"      → Fallback a PyPDF...")
            with open(pdf_path, 'rb') as file:
                reader = pypdf.PdfReader(file)
                pdf_docs = []
                
                for page_num, page in enumerate(reader.pages, 1):
                    text = page.extract_text()
                    if text and text.strip():
                        pdf_docs.append(Document(
                            page_content=text,
                            metadata={"source": str(pdf_path), "page": page_num - 1}
                        ))
                
                if pdf_docs:
                    docs.extend(pdf_docs)
                    print(f"      ✅ Cargado ({len(pdf_docs)} páginas)")
                else:
                    print(f"      ⚠️  No se extrajo texto (PDF escaneado?)")
        except Exception as e:
            print(f"      ❌ Error con PyPDF: {e}")
    
    if not docs:
        print(f"\n❌ No se pudo extraer contenido de ningún PDF")
        print(f"   Soluciones:")
        print(f"   - Si son PDFs escaneados, instala OCR:")
        print(f"     brew install tesseract poppler")
        sys.exit(1)
    
    print(f"\n✅ Total de documentos cargados: {len(docs)}")

except Exception as e:
    print(f"❌ Error cargando librerías: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. Dividir en chunks
print(f"\n3️⃣  Dividiendo documentos en chunks...")
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunks = splitter.split_documents(docs)
    print(f"✅ Se generaron {len(chunks)} chunks")
    
    if not chunks:
        print(f"❌ No se generaron chunks")
        sys.exit(1)

except Exception as e:
    print(f"❌ Error dividiendo documentos: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Generar embeddings
print(f"\n4️⃣  Generando embeddings...")
try:
    from langchain_ollama import OllamaEmbeddings
    
    MODEL_NAME = sys.argv[1] if len(sys.argv) > 1 else "llama3.1"
    EMBED_MODEL = "nomic-embed-text"
    
    # Verificar ollama
    print(f"   🦙 Verificando ollama...")
    result = subprocess.run(
        ["ollama", "list"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode != 0:
        print(f"❌ Ollama no responde")
        print(f"   Solución: Ejecuta 'ollama serve' en otra terminal")
        sys.exit(1)
    
    print(f"   ✅ Ollama disponible")
    
    # Verificar modelo embeddings
    if EMBED_MODEL.lower() not in result.stdout.lower():
        print(f"   ⬇️  Descargando {EMBED_MODEL}...")
        pull_result = subprocess.run(
            ["ollama", "pull", EMBED_MODEL],
            capture_output=True,
            text=True,
            timeout=300
        )
        if pull_result.returncode != 0:
            print(f"❌ Error al descargar {EMBED_MODEL}")
            print(f"   {pull_result.stderr}")
            sys.exit(1)
    else:
        print(f"   ✅ {EMBED_MODEL} disponible")
    
    # Crear embeddings
    print(f"   🔗 Conectando a Ollama...")
    embeddings = OllamaEmbeddings(
        model=EMBED_MODEL,
        base_url="http://localhost:11434"
    )
    print(f"   ✅ Embeddings listo")

except subprocess.TimeoutExpired:
    print(f"❌ Ollama no responde (timeout)")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error con embeddings: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 5. Crear ChromaDB
print(f"\n5️⃣  Creando base de datos vectorial...")
try:
    import chromadb
    
    # Limpiar cache y asegurar ruta absoluta
    DB_PATH = os.path.abspath(DB_DIR)
    os.makedirs(DB_PATH, exist_ok=True)
    print(f"   📁 Ruta DB: {DB_PATH}")
    
    # Conectar con client persistente
    client = chromadb.PersistentClient(path=DB_PATH)
    print(f"   ✅ Cliente ChromaDB conectado")
    
    # Eliminar colección anterior si existe
    try:
        client.delete_collection("documents")
        print(f"   🗑️  Colección anterior eliminada")
    except:
        pass
    
    # Crear colección
    collection = client.create_collection(
        name="documents",
        metadata={"hnsw:space": "cosine"}
    )
    print(f"   ✅ Nueva colección 'documents' creada")
    
    # Agregar chunks
    print(f"   📥 Agregando {len(chunks)} chunks a la BD...")
    batch_ids = []
    batch_embeddings = []
    batch_documents = []
    batch_metadatas = []
    
    for i, chunk in enumerate(chunks):
        try:
            # Generar embedding
            embedding = embeddings.embed_query(chunk.page_content)
            
            # Agregar a batch
            batch_ids.append(f"chunk_{i}")
            batch_embeddings.append(embedding)
            batch_documents.append(chunk.page_content)
            batch_metadatas.append(chunk.metadata or {"source": "unknown"})
            
            # Mostrar progreso
            if (i + 1) % 5 == 0:
                print(f"      ✓ {i + 1}/{len(chunks)}")
        except Exception as e:
            print(f"      ❌ Error en chunk {i}: {e}")
            continue
    
    # Agregar batch completo a la colección
    if batch_ids:
        collection.add(
            ids=batch_ids,
            embeddings=batch_embeddings,
            documents=batch_documents,
            metadatas=batch_metadatas
        )
        print(f"   ✅ {len(batch_ids)} chunks agregados a ChromaDB")
    else:
        print(f"   ❌ No hay chunks para agregar")
        sys.exit(1)

except Exception as e:
    print(f"❌ Error creando BD: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 6. Verificar
print(f"\n6️⃣  Verificando BD...")
try:
    result = collection.get(include=["documents"])
    stored_docs = result.get("documents", [])
    print(f"   ✅ {len(stored_docs)} documentos almacenados en colección")
    
    if not stored_docs:
        print(f"   ⚠️  La colección está vacía")
    
    # Verificar desde cliente nuevo para asegurar persistencia
    print(f"   ✅ Verificando persistencia...")
    test_client = chromadb.PersistentClient(path=DB_PATH)
    test_col = test_client.get_collection("documents")
    test_result = test_col.get(include=["documents"])
    test_docs = test_result.get("documents", [])
    print(f"   ✅ {len(test_docs)} documentos persiste en disco")
    
    if not test_docs:
        print(f"❌ Fallo en persistencia")
        sys.exit(1)

except Exception as e:
    print(f"❌ Error verificando: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ✨ Éxito
print(f"\n{'='*70}")
print(f"✨ ¡INDEXACIÓN COMPLETADA EXITOSAMENTE!")
print(f"{'='*70}")
print(f"📊 Resumen:")
print(f"   - PDFs procesados: {len(pdf_files)}")
print(f"   - Documentos extraídos: {len(docs)}")
print(f"   - Chunks generados: {len(chunks)}")
print(f"   - Base de datos: {DB_DIR}/")
print(f"   - Colección: documents")
print(f"   - Estado: ✅ LISTO\n")

sys.exit(0)
