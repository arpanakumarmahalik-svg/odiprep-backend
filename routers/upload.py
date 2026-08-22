from fastapi import APIRouter, UploadFile, File, HTTPException
from services.file_parser import extract_text
import os
import uuid

router = APIRouter()

# Allowed file types
ALLOWED_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain"
]

UPLOAD_FOLDER = "uploads"

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Check file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOCX, PPT, and TXT files are allowed"
        )

    # Read and save the file
    content = await file.read()
    file_id = str(uuid.uuid4())
    extension = file.filename.split(".")[-1]
    saved_filename = f"{file_id}.{extension}"
    saved_path = os.path.join(UPLOAD_FOLDER, saved_filename)

    with open(saved_path, "wb") as f:
        f.write(content)

    # Extract text immediately after saving
    extracted_text = extract_text(saved_path)

    # Check if text was actually extracted
    if not extracted_text:
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from this file. Make sure it has readable content."
        )

    return {
        "file_id": file_id,
        "filename": file.filename,
        "file_type": file.content_type,
        "file_size_kb": round(len(content) / 1024, 2),
        "characters_extracted": len(extracted_text),
        "text_preview": extracted_text[:200],
        "message": "File uploaded and text extracted successfully"
    }