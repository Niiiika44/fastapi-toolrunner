import io

import pytest
from PIL import Image

from app.core.config import get_settings
from app.users.avatar_image import OUTPUT_FORMAT, encode_avatar
from app.users.exceptions import ImageDecodeError, UnsupportedImageError
from tests.factories import make_image_bytes

settings = get_settings()


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP"])
def test_accepts_every_supported_format(fmt):
    encoded = encode_avatar(make_image_bytes(fmt=fmt))
    assert Image.open(io.BytesIO(encoded)).format == OUTPUT_FORMAT


def test_squares_and_shrinks():
    encoded = encode_avatar(make_image_bytes(width=1600, height=400))
    side = settings.AVATAR_SIZE_PX
    assert Image.open(io.BytesIO(encoded)).size == (side, side)


def test_output_is_smaller_than_input():
    raw = make_image_bytes(width=2000, height=2000)
    assert len(encode_avatar(raw)) < len(raw)


def test_keeps_transparency():
    encoded = encode_avatar(make_image_bytes(transparent=True))
    image = Image.open(io.BytesIO(encoded)).convert("RGBA")
    centre = settings.AVATAR_SIZE_PX // 2
    assert image.getpixel((centre, centre))[3] == 0


def test_drops_opaque_alpha_channel():
    encoded = encode_avatar(make_image_bytes())
    assert Image.open(io.BytesIO(encoded)).mode == "RGB"


@pytest.mark.parametrize("payload", [
    b"%PDF-1.7\n%\xe2\xe3\xcf\xd3" + b"\x00" * 64,
    b"GIF89a" + b"\x00" * 64,
    b"",
    b"\x89PN",
])
def test_rejects_unsupported_signature(payload):
    with pytest.raises(UnsupportedImageError):
        encode_avatar(payload)


def test_rejects_file_lying_about_its_signature():
    with pytest.raises(ImageDecodeError):
        encode_avatar(b"\x89PNG\r\n\x1a\n" + b"not an image at all" * 32)


def test_rejects_too_many_pixels():
    side = int(settings.AVATAR_MAX_PIXELS ** 0.5) + 500
    raw = make_image_bytes(width=side, height=side, fmt="PNG")
    assert len(raw) < settings.AVATAR_MAX_BYTES, "the bomb must pass the byte limit"
    with pytest.raises(ImageDecodeError):
        encode_avatar(raw)
