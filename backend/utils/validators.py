import os
import re
from urllib.parse import urlparse

RATIO_RE = re.compile(r"^\d{1,3}:\d{1,3}$")


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

