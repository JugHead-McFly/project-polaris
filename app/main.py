from fastapi import FastAPI, UploadFile, File
from parser.fits_parser import parse_fits
import tempfile
import os

app = FastAPI(title="Doug's Observatory API")

@app.get("/")
def root():
    return {"status": "Doug's Observatory API is running"}

@app.post("/parse-fits")
async def parse_fits_upload(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename)[1] or ".fits"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        result = parse_fits(tmp_path)
        result["filename"] = file.filename
        return result
    finally:
        os.remove(tmp_path)
