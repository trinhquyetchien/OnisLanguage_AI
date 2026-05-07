from fastapi import HTTPException, UploadFile
from pathlib import Path

def validate_extension(file: UploadFile, allowed: set):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    suffix = f".{file.filename.split('.')[-1].lower()}"
    if suffix not in allowed:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file extension: {suffix}. Supported: {', '.join(allowed)}"
        )
    return suffix
