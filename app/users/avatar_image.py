import io

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings
from app.users.exceptions import ImageDecodeError, UnsupportedImageError

settings = get_settings()

Image.MAX_IMAGE_PIXELS = settings.AVATAR_MAX_PIXELS

OUTPUT_FORMAT = "WEBP"
OUTPUT_EXTENSION = "webp"
OUTPUT_MEDIA_TYPE = "image/webp"
_QUALITY = 82

_PNG = b"\x89PNG\r\n\x1a\n"
_JPEG = b"\xff\xd8\xff"
_RIFF = b"RIFF"
_WEBP = b"WEBP"


def _is_supported(raw: bytes) -> bool:
    if raw.startswith(_PNG) or raw.startswith(_JPEG):
        return True
    return raw.startswith(_RIFF) and raw[8:12] == _WEBP


def _open_within_limits(raw: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(raw))
    if image.width * image.height > settings.AVATAR_MAX_PIXELS:
        image.close()
        raise ImageDecodeError()
    return image


def encode_avatar(raw: bytes) -> bytes:
    if not _is_supported(raw):
        raise UnsupportedImageError()

    side = settings.AVATAR_SIZE_PX
    try:
        with _open_within_limits(raw) as probe:
            probe.verify()

        with _open_within_limits(raw) as opened:
            oriented = ImageOps.exif_transpose(opened)
            square = ImageOps.fit(oriented, (side, side), Image.Resampling.LANCZOS)
            if square.mode not in ("RGB", "RGBA"):
                square = square.convert("RGBA")

            buffer = io.BytesIO()
            square.save(buffer, format=OUTPUT_FORMAT, quality=_QUALITY, method=4)
            return buffer.getvalue()
    except ImageDecodeError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError) as exc:
        raise ImageDecodeError() from exc
