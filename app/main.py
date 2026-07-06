from fastapi import FastAPI, UploadFile, File
from parser.fits_parser import parse_fits
from app.database.database import SessionLocal
from app.services.capture_service import create_capture_from_parsed_fits

import tempfile
import os

app = FastAPI(title="Project Polaris API")


@app.get("/")
def root():
    return {"status": "Project Polaris API is running"}


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


@app.post("/ingest-fits")
async def ingest_fits_upload(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename)[1] or ".fits"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    db = SessionLocal()

    try:
        parsed = parse_fits(tmp_path)
        capture = create_capture_from_parsed_fits(
            db=db,
            parsed=parsed,
            filename=file.filename,
        )

        return {
            "status": "saved",
            "capture": {
                "id": capture.id,
                "object_name": capture.object_name,
                "filename": capture.filename,
                "observation_utc": capture.observation_utc,
                "gain": capture.gain,
                "ra": capture.ra,
                "dec": capture.dec,
                "telescope": capture.telescope,
                "firmware": capture.firmware,
            },
            "parsed": parsed,
        }
    finally:
        db.close()
        os.remove(tmp_path)