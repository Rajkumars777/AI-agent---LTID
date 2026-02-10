from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
from capabilities.browser import browse_url, screenshot_url

router = APIRouter(prefix="/tools", tags=["tools"])

@router.get("/files")
async def get_files(directory: str = "."):
    """List files in a directory."""
    try:
        return {"files": os.listdir(directory)}
    except FileNotFoundError:
        return {"files": [], "error": f"Directory {directory} not found"}

class BrowseRequest(BaseModel):
    url: str

@router.post("/browser/browse")
async def browse(request: BrowseRequest):
    """Browse a URL and return title/content."""
    return await browse_url(request.url)

class ScreenshotRequest(BaseModel):
    url: str
    output_path: str = "screenshot.png"

@router.post("/browser/screenshot")
async def screenshot(request: ScreenshotRequest):
    """Take a screenshot of a URL."""
    path = await screenshot_url(request.url, request.output_path)
    return {"status": "success", "path": path}
