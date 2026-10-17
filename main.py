import os
import shutil
import zipfile
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from PIL import Image

app = FastAPI(title="Can Studio - Enterprise Universal Converter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "storage_uploads"
OUTPUT_DIR = "storage_outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def read_index():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>index.html bulunamadı!</h1>"

@app.post("/api/convert-batch")
async def convert_batch(
    files: List[UploadFile] = File(...),
    target_format: str = Form(...)
):
    try:
        target = target_format.lower()
        converted_files = []

        for file in files:
            base_name, _ = os.path.splitext(file.filename)
            output_filename = f"{base_name}.{target}"
            
            input_path = os.path.join(UPLOAD_DIR, file.filename)
            output_path = os.path.join(OUTPUT_DIR, output_filename)

            with open(input_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            file_ext = file.filename.split(".")[-1].lower()

            # Görselden Görsele / PDF'e Dönüşüm Mantığı
            if file_ext in ["png", "jpg", "jpeg", "webp"] and target in ["png", "jpg", "jpeg", "webp"]:
                img = Image.open(input_path)
                if target in ["jpg", "jpeg"]:
                    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        if img.mode == "P":
                            img = img.convert("RGBA")
                        background.paste(img, mask=img.split()[-1])
                        img = background
                    elif img.mode != "RGB":
                        img = img.convert("RGB")
                    img.save(output_path, "JPEG", quality=95)
                elif target == "png":
                    img.save(output_path, "PNG")
                elif target == "webp":
                    img.save(output_path, "WEBP", quality=95)
            elif file_ext in ["png", "jpg", "jpeg", "webp"] and target == "pdf":
                img = Image.open(input_path)
                if img.mode in ("RGBA", "P"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(img, mask=img.split()[-1])
                    img = background
                img.save(output_path, "PDF", resolution=100.0)
            else:
                shutil.copy(input_path, output_path)

            converted_files.append(output_path)

        # Tek dosya ise doğrudan, çoklu dosya ise ZIP olarak paketle
        if len(converted_files) == 1:
            return FileResponse(
                converted_files[0], 
                filename=os.path.basename(converted_files[0]), 
                media_type="application/octet-stream"
            )
        else:
            zip_path = os.path.join(OUTPUT_DIR, "can_studio_converted.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for fpath in converted_files:
                    zipf.write(fpath, os.path.basename(fpath))
            return FileResponse(
                zip_path, 
                filename="can_studio_converted.zip", 
                media_type="application/zip"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)