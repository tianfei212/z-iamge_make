"""
/**
 * @file backend/controllers/images_controller.py
 * @description 图片列表与缩略图控制器。
 */
"""

from __future__ import annotations

import os
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response

from backend.config import load_settings
from backend.utils import decode_image_id, encode_image_id, safe_dir_name, safe_join


router = APIRouter()


def _list_output_images(output_dir: str, category: Optional[str], limit: int, offset: int) -> List[Dict[str, Any]]:
    base = os.path.abspath(output_dir)
    if not os.path.isdir(base):
        return []

    items: List[Dict[str, Any]] = []
    categories = []
    if category:
        categories = [safe_dir_name(category)]
    else:
        try:
            categories = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
        except OSError:
            categories = []

    for cat in categories:
        if cat.startswith("."):
            continue
        cat_dir = os.path.join(base, cat)
        if not os.path.isdir(cat_dir):
            continue
        try:
            filenames = os.listdir(cat_dir)
        except OSError:
            continue
        for filename in filenames:
            if filename.startswith("."):
                continue
            full_path = os.path.join(cat_dir, filename)
            if not os.path.isfile(full_path):
                continue
            try:
                stat = os.stat(full_path)
            except OSError:
                continue
            rel_path = f"{cat}/{filename}"
            image_id = encode_image_id(rel_path)
            items.append(
                {
                    "id": image_id,
                    "category": cat,
                    "filename": filename,
                    "timestamp": int(stat.st_mtime * 1000),
                    "originalUrl": f"/api/images/{image_id}/raw",
                    "thumbUrl": f"/api/images/{image_id}/thumb",
                    "url": f"/api/images/{image_id}/thumb",
                }
            )

    items.sort(key=lambda x: int(x.get("timestamp") or 0), reverse=True)
    return items[offset : offset + limit]


@router.get("/api/images")
def list_images(
    category: Optional[str] = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    settings = load_settings()
    images = _list_output_images(settings.output_dir, category=category, limit=limit, offset=offset)
    return {"images": images}


@router.get("/api/images/{image_id}/raw")
def get_raw_image(image_id: str):
    settings = load_settings()
    rel = decode_image_id(image_id)
    if not rel:
        raise HTTPException(status_code=404, detail={"status": "error", "message": "Not found"})
    full_path = safe_join(settings.output_dir, rel)
    if not full_path or not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail={"status": "error", "message": "Not found"})
    return FileResponse(full_path)


@router.get("/api/images/{image_id}/thumb")
def get_thumbnail(image_id: str, size: int = Query(512, ge=64, le=1024)):
    settings = load_settings()
    rel = decode_image_id(image_id)
    if not rel:
        raise HTTPException(status_code=404, detail={"status": "error", "message": "Not found"})
    src_path = safe_join(settings.output_dir, rel)
    if not src_path or not os.path.isfile(src_path):
        raise HTTPException(status_code=404, detail={"status": "error", "message": "Not found"})

    thumb_root = os.path.join(os.path.abspath(settings.output_dir), ".thumbs", str(size))
    thumb_rel = os.path.splitext(rel)[0] + ".jpg"
    thumb_path = safe_join(thumb_root, thumb_rel)
    if not thumb_path:
        raise HTTPException(status_code=500, detail={"status": "error", "message": "Invalid thumbnail path"})

    try:
        os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
    except OSError:
        raise HTTPException(status_code=500, detail={"status": "error", "message": "Cannot create thumbnail directory"})

    try:
        src_mtime = os.path.getmtime(src_path)
        if os.path.isfile(thumb_path) and os.path.getmtime(thumb_path) >= src_mtime:
            return FileResponse(thumb_path, media_type="image/jpeg")
    except OSError:
        pass

    try:
        from PIL import Image
    except Exception:
        return FileResponse(src_path)

    try:
        with Image.open(src_path) as im:
            im.load()
            info = getattr(im, "info", {}) or {}
            if getattr(im, "mode", None) in ("RGBA", "LA") or ("transparency" in info):
                if getattr(im, "mode", None) not in ("RGBA", "LA"):
                    im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[-1])
                im = bg
            else:
                im = im.convert("RGB")
            im.thumbnail((size, size), Image.LANCZOS)
            buf = BytesIO()
            im.save(buf, format="JPEG", quality=82, optimize=True)
            data = buf.getvalue()
    except Exception:
        return FileResponse(src_path)

    try:
        with open(thumb_path, "wb") as f:
            f.write(data)
    except OSError:
        return Response(content=data, media_type="image/jpeg")

    return FileResponse(thumb_path, media_type="image/jpeg")
