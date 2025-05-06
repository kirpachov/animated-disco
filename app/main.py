import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import shutil
from typing import List
import asyncio
from concurrent.futures import ThreadPoolExecutor
import aiofiles
from datetime import datetime

app = FastAPI()

# Configurazione ottimizzata
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 1024 * 1024 * 20  # 20MB per file
MAX_TOTAL_SIZE = 1024 * 1024 * 200 * 1024  # 2GB totale
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.heif'}
MAX_WORKERS = 4  # Thread per il processing parallelo

# Crea la cartella uploads se non esiste
Path(UPLOAD_DIR).mkdir(exist_ok=True)

# Monta la cartella uploads come statica per verifica immediata
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Thread pool per operazioni I/O
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

async def save_file(file: UploadFile, upload_dir: str):
    """Salva un file in modo asincrono ed efficiente"""
    try:
        file_path = os.path.join(upload_dir, file.filename)
        
        # Evita sovrascritture
        counter = 1
        while os.path.exists(file_path):
            name, ext = os.path.splitext(file.filename)
            file_path = os.path.join(upload_dir, f"{name}_{counter}{ext}")
            counter += 1
        
        # Usa aiofiles per I/O asincrono
        async with aiofiles.open(file_path, 'wb') as buffer:
            while chunk := await file.read(1024 * 1024):  # Legge in chunk da 1MB
                await buffer.write(chunk)
        
        return file_path
    except Exception as e:
        raise e
    finally:
        await file.close()

@app.get("/", response_class=HTMLResponse)
async def upload_form():
    return """
    <html>
        <head>
            <title>Caricamento File Ottimizzato</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>
            <h1>Carica foto da iPhone</h1>

            <a style="display: block; margin: 2em;" href="/gallery">Galleria</a>

            <form action="/uploadfiles/" enctype="multipart/form-data" method="post" id="uploadForm">
                <input name="files" type="file" multiple accept="image/*">
                <div id="progressContainer" style="display: none;">
                    <progress id="uploadProgress" value="0" max="100"></progress>
                    <span id="progressText">0%</span>
                </div>
                <input type="submit" id="submitBtn">
            </form>
            <script>
                document.getElementById('uploadForm').addEventListener('submit', function(e) {
                    const progressContainer = document.getElementById('progressContainer');
                    const progressBar = document.getElementById('uploadProgress');
                    const progressText = document.getElementById('progressText');
                    const submitBtn = document.getElementById('submitBtn');
                    
                    progressContainer.style.display = 'block';
                    submitBtn.disabled = true;
                    
                    const xhr = new XMLHttpRequest();
                    xhr.upload.onprogress = function(event) {
                        if (event.lengthComputable) {
                            const percentComplete = Math.round((event.loaded / event.total) * 100);
                            progressBar.value = percentComplete;
                            progressText.textContent = percentComplete + '%';
                        }
                    };
                    
                    xhr.open('POST', '/uploadfiles/', true);
                    xhr.onload = function() {
                        if (xhr.status === 200) {
                            alert('Caricamento completato!');
                        } else {
                            alert('Errore nel caricamento: ' + xhr.responseText);
                        }
                        submitBtn.disabled = false;
                    };
                    
                    const formData = new FormData(this);
                    xhr.send(formData);
                    e.preventDefault();
                });
            </script>
        </body>
    </html>
    """

@app.post("/uploadfiles/")
async def create_upload_files(files: List[UploadFile] = File(...)):
    total_size = 0
    tasks = []
    
    # Verifica preliminare dei file
    for file in files:
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Formato non supportato: {file_extension}")
        
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"File troppo grande: {file.filename} ({file_size/1024/1024:.1f}MB)")
        
        total_size += file_size
    
    if total_size > MAX_TOTAL_SIZE:
        raise HTTPException(status_code=400, detail=f"Dimensione totale supera il limite di {MAX_TOTAL_SIZE/1024/1024}MB")
    
    # Processa i file in parallelo
    try:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                executor,
                lambda f=file: asyncio.run(save_file(f, UPLOAD_DIR))
            ) for file in files
        ]
        
        saved_files = await asyncio.gather(*tasks)
        return {"saved_files": saved_files, "total_size": f"{total_size/1024/1024:.1f}MB"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/gallery")
async def view_gallery():
    # Ottieni lista file nella cartella uploads
    image_files = []
    for file in os.listdir(UPLOAD_DIR):
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.heic', '.heif')):
            image_files.append(file)
    
    # Ordina per data di creazione (dal più recente)
    image_files.sort(key=lambda x: os.path.getmtime(os.path.join(UPLOAD_DIR, x)), reverse=True)
    
    # Genera HTML
    gallery_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Galleria Foto</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background-color: #f5f5f7;
                padding: 10px;
            }
            .header {
                text-align: center;
                padding: 15px 0;
                position: sticky;
                top: 0;
                background-color: #f5f5f7;
                z-index: 100;
            }
            .gallery {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 8px;
                margin-bottom: 60px;
            }
            .photo {
                width: 100%;
                aspect-ratio: 1;
                object-fit: cover;
                border-radius: 8px;
                background: #eee;
                transition: transform 0.2s;
            }
            .photo:active {
                transform: scale(0.95);
            }
            .footer {
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                background: white;
                padding: 10px;
                display: flex;
                justify-content: space-around;
                box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
            }
            .nav-button {
                padding: 10px 20px;
                background: #007aff;
                color: white;
                border-radius: 20px;
                text-decoration: none;
                font-weight: 500;
            }
            .empty {
                grid-column: 1 / -1;
                text-align: center;
                padding: 40px 0;
                color: #888;
            }
            @media (min-width: 768px) {
                .gallery {
                    grid-template-columns: repeat(3, 1fr);
                }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Le tue foto</h2>
        </div>
        
        <div class="gallery">
    """
    
    if not image_files:
        gallery_html += """
            <div class="empty">
                <p>Nessuna foto ancora caricata</p>
            </div>
        """
    else:
        for img in image_files:
            gallery_html += f"""
            <a href="/uploads/{img}" target="_blank">
                <img src="/uploads/{img}" class="photo" loading="lazy">
            </a>
            """
    
    gallery_html += """
        </div>
        
        <div class="footer">
            <a href="/" class="nav-button">Nuovo Caricamento</a>
        </div>
        
        <script>
            // Infinite scroll
            let loading = false;
            window.addEventListener('scroll', function() {
                if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 500 && !loading) {
                    loading = true;
                    // Qui potresti aggiungere caricamento lazy di più immagini
                    // se implementi la paginazione lato server
                }
            });
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=gallery_html)