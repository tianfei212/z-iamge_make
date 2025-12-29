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
from backend.services.db_service import DBService


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


@router.get("/api/images/by-filename/{filename}/details")
def get_image_details_by_filename(filename: str, category: Optional[str] = None):
    settings = load_settings()
    base = os.path.abspath(settings.output_dir)
    if not os.path.isdir(base):
        raise HTTPException(status_code=404, detail={"status": "error", "message": "Output dir not found"})
    fname = (filename or "").strip()
    if not fname:
        raise HTTPException(status_code=422, detail={"status": "error", "message": "Filename required"})
    cat = safe_dir_name(category) if category else None
    rel_path: Optional[str] = None
    full_path: Optional[str] = None
    if cat:
        rel_path = f"{cat}/{fname}"
        full_path = safe_join(settings.output_dir, rel_path)
        if not full_path or not os.path.isfile(full_path):
            # fallback: not found under provided category
            rel_path = None
            full_path = None
    if rel_path is None:
        try:
            cats = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
        except OSError:
            cats = []
        for c in cats:
            if c.startswith("."):
                continue
            p = os.path.join(base, c, fname)
            if os.path.isfile(p):
                rel_path = f"{c}/{fname}"
                full_path = p
                break
    if not rel_path or not full_path:
        raise HTTPException(status_code=404, detail={"status": "error", "message": "File not found"})
    try:
        st = os.stat(full_path)
        ts = int(st.st_mtime * 1000)
    except OSError:
        ts = int(os.path.getmtime(full_path)) if os.path.exists(full_path) else int((__import__("time").time()) * 1000)
    image_id = encode_image_id(rel_path)
    image = {
        "id": image_id,
        "category": rel_path.split("/")[0],
        "filename": fname,
        "timestamp": ts,
        "originalUrl": f"/api/images/{image_id}/raw",
        "thumbUrl": f"/api/images/{image_id}/thumb",
        "url": f"/api/images/{image_id}/thumb",
    }
    svc = DBService()
    # First try precise match on relative_url
    with __import__("contextlib").closing(__import__("sqlite3").connect(__import__("os").path.join(os.path.dirname(os.path.dirname(__file__)), "data", "app.db"))) as _:
        pass
    # Query items by relative_url
    from backend.db.connection import get_conn
    record_row: Optional[Dict[str, Any]] = None
    with get_conn() as conn:
        cur = conn.execute("SELECT record_id,id FROM items WHERE relative_url=? ORDER BY id DESC LIMIT 1", (rel_path,))
        row = cur.fetchone()
        if not row:
            # fallback: match by absolute_path suffix
            cur = conn.execute("SELECT record_id,id,absolute_path FROM items ORDER BY id DESC")
            rec_id = None
            for r in cur.fetchall():
                ap = str(r[2] or "")
                if ap.replace("\\", "/").endswith(rel_path):
                    rec_id = int(r[0])
                    break
            if rec_id is not None:
                record_row = svc.get_record(rec_id)
        else:
            rec_id = int(row[0])
            record_row = svc.get_record(rec_id)
    if not record_row:
        # Not recorded; still return image basic info with empty prompts
        return {
            "image": image,
            "prompts": {
                "positive": None,
                "negative": None,
                "base_prompt": None,
                "category_prompt": None,
            },
            "meta": {}
        }
    prompts = {
        "positive": record_row.get("refined_positive"),
        "negative": record_row.get("refined_negative"),
        "base_prompt": record_row.get("base_prompt"),
        "category_prompt": record_row.get("category_prompt"),
    }
    meta = {
        "aspect_ratio": record_row.get("aspect_ratio"),
        "quality": record_row.get("quality"),
        "model_name": record_row.get("model_name"),
        "created_at": record_row.get("created_at"),
        "status": record_row.get("status"),
    }
    return {"image": image, "prompts": prompts, "meta": meta}
