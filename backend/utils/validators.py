import os
import re
from urllib.parse import urlparse

RATIO_RE = re.compile(r"^\d{1,3}:\d{1,3}$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[45][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)


def is_valid_ratio(value: str) -> bool:
    return bool(RATIO_RE.fullmatch(value.strip()))


def is_valid_quality(value: str, allowed: set) -> bool:
    return value.strip() in allowed


def is_valid_url(value: str) -> bool:
    v = value.strip()
    try:
        parsed = urlparse(v)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def is_valid_relative_image_path(value: str) -> bool:
    v = value.strip()
    return v.startswith("/api/images/") and (v.endswith("/raw") or v.endswith("/thumb"))


def is_absolute_path(value: str) -> bool:
    return os.path.isabs(value.strip())


def is_valid_uuid(value: str) -> bool:
    v = value.strip()
    return bool(UUID_RE.fullmatch(v))
