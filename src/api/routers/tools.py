from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os


router = APIRouter(prefix="/tools", tags=["tools"])

@router.get("/files")
async def get_files(directory: str = "."):
    """List files in a directory."""
    try:
        return {"files": os.listdir(directory)}
    except FileNotFoundError:
        return {"files": [], "error": f"Directory {directory} not found"}


