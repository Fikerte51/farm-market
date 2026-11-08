"""Lot photos: validated JPG/PNG files are stored on disk under uploads/ and their relative path is
stored in MySQL (harvest_lot_images). Files survive an application restart; a missing file is
handled gracefully by the GUI."""
import io
import uuid
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from . import config, db
from .core import User, deny, is_my_farm, log_event, lot_farm, req_text, require_role
from .errors import UserError

_ALLOWED_PREFIXES = ("images/", "uploads/")


def detect_mime(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    return None


def validate_image(filename: str, data: bytes) -> str:
    """Return the real MIME type or raise a friendly error."""
    if not data:
        raise UserError("The selected file is empty.")
    if len(data) > config.MAX_IMAGE_BYTES:
        raise UserError(f"This image is {len(data) / 1048576:.1f} MB. Images must be 5 MB or smaller.")
    if not (filename or "").lower().endswith((".jpg", ".jpeg", ".png")):
        raise UserError("Only .jpg, .jpeg and .png files can be uploaded.")
    mime = detect_mime(data)
    if mime is None:
        raise UserError(f'"{filename}" is not really a JPG or PNG (it may be a renamed WEBP, HEIC or other format). '
                        "Please save it as JPG or PNG and try again.")
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
        raise UserError("The image file is damaged or unreadable. Please choose another file.") from None
    return mime


def resolve_path(rel_path: str) -> Path | None:
    """Absolute path of a stored image, or None if it is unsafe or the file is missing."""
    if not rel_path or not rel_path.startswith(_ALLOWED_PREFIXES) or ".." in Path(rel_path).parts:
        return None
    full = (config.BASE_DIR / rel_path).resolve()
    try:
        full.relative_to(config.BASE_DIR)
    except ValueError:
        return None
    return full if full.is_file() else None


def load_image_bytes(rel_path: str) -> bytes | None:
    p = resolve_path(rel_path)
    if p is None:
        return None
    try:
        return p.read_bytes()
    except OSError:
        return None


def add_lot_image(user: User, lot_id: int, filename: str, data: bytes, caption: str | None = None) -> int:
    require_role(user, "farmer", "upload lot image")
    caption = req_text(caption, "Caption", False, 200)
    mime = validate_image(filename, data)
    ext = "png" if mime == "image/png" else "jpg"
    with db.transaction() as cur:
        farm = lot_farm(cur, lot_id)
        if farm is None:
            raise UserError("Harvest lot not found.")
        if not is_my_farm(cur, user, farm):
            deny(user, "upload image to another farm's lot", "harvest_lots", lot_id)
        rel = f"uploads/lot_{lot_id}/{uuid.uuid4().hex}.{ext}"
        full = config.BASE_DIR / rel
        try:
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_bytes(data)
        except OSError:
            raise UserError("The image could not be saved on disk. Please try again.") from None
        try:
            cur.execute("INSERT INTO harvest_lot_images (lot_id, file_path, mime_type, caption, uploaded_by) "
                        "VALUES (%s,%s,%s,%s,%s)", (lot_id, rel, mime, caption, user.user_id))
            image_id = cur.lastrowid
            log_event(cur, user, "IMAGE_UPLOADED", "harvest_lot_images", image_id, f"lot #{lot_id}")
        except BaseException:
            full.unlink(missing_ok=True)
            raise
    return image_id


def remove_lot_image(user: User, image_id: int) -> None:
    """Soft-remove: the row is kept (history), the photo just stops being shown."""
    require_role(user, "farmer", "remove lot image")
    with db.transaction() as cur:
        cur.execute("SELECT lot_id FROM harvest_lot_images WHERE image_id=%s AND is_active=1 FOR UPDATE", (image_id,))
        row = cur.fetchone()
        if row is None:
            raise UserError("Image not found.")
        if not is_my_farm(cur, user, lot_farm(cur, row["lot_id"])):
            deny(user, "remove image from another farm's lot", "harvest_lot_images", image_id)
        cur.execute("UPDATE harvest_lot_images SET is_active=0 WHERE image_id=%s", (image_id,))
        log_event(cur, user, "IMAGE_REMOVED", "harvest_lot_images", image_id, f"lot #{row['lot_id']}")


def display_bytes(rel_path: str) -> bytes | None:
    """Image bytes only if the file exists AND decodes, so the GUI can show a friendly note instead of crashing."""
    data = load_image_bytes(rel_path)
    if data is None:
        return None
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
        return None
    return data
