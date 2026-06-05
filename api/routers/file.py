"""文件操作路由：/api/file/*"""
import os, sys

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/file", tags=["file"])


@router.post("/read")
async def read_file(data: dict):
    path = data.get("file_path", "")
    if not path:
        raise HTTPException(status_code=400, detail="file_path is required")
    try:
        path = os.path.expanduser(path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"type": "text", "file_path": path, "content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/write")
async def write_file(data: dict):
    path = data.get("file_path", "")
    content = data.get("content", "")
    if not path:
        raise HTTPException(status_code=400, detail="file_path is required")
    try:
        path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"success": True, "file_path": path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/list")
async def list_files(data: dict):
    path = data.get("path", ".")
    try:
        path = os.path.expanduser(path)
        files = os.listdir(path)
        return [{"name": f, "path": os.path.join(path, f)} for f in files]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/delete")
async def delete_file(data: dict):
    path = data.get("file_path", "")
    if not path:
        raise HTTPException(status_code=400, detail="file_path is required")
    try:
        path = os.path.expanduser(path)
        os.remove(path)
        return {"success": True}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
