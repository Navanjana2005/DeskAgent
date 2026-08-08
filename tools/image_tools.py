"""
tools/image_tools.py
Image processing tools using Pillow (PIL) and qrcode.

Required packages: pip install Pillow qrcode[pil]
"""

import os
from langchain_core.tools import tool

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


def _check_pillow():
    if not HAS_PILLOW:
        return "❌ Pillow not installed. Run: pip install Pillow"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def resize_image(input_path: str, output_path: str, width: int = 0, height: int = 0, scale_percent: int = 0) -> str:
    """Resizes an image to specific dimensions or a percentage of the original.

    Args:
        input_path: Path to the source image.
        output_path: Path to save the resized image.
        width: Target width in pixels (0 = auto from height or scale).
        height: Target height in pixels (0 = auto from width or scale).
        scale_percent: Scale percentage (e.g., 50 = half size). Overrides width/height if set.
    """
    err = _check_pillow()
    if err:
        return err
    try:
        img = Image.open(input_path)
        orig_w, orig_h = img.size

        if scale_percent > 0:
            new_w = int(orig_w * scale_percent / 100)
            new_h = int(orig_h * scale_percent / 100)
        elif width > 0 and height > 0:
            new_w, new_h = width, height
        elif width > 0:
            ratio = width / orig_w
            new_w, new_h = width, int(orig_h * ratio)
        elif height > 0:
            ratio = height / orig_h
            new_w, new_h = int(orig_w * ratio), height
        else:
            return "❌ Provide width, height, or scale_percent."

        resized = img.resize((new_w, new_h), Image.LANCZOS)
        resized.save(output_path)
        return (
            f"✅ Image resized\n"
            f"Original: {orig_w}×{orig_h}\n"
            f"New size: {new_w}×{new_h}\n"
            f"Saved to: {output_path}"
        )
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def convert_image_format(input_path: str, output_path: str) -> str:
    """Converts an image to a different format (PNG, JPG, WEBP, BMP, TIFF, ICO).

    Args:
        input_path: Path to the source image.
        output_path: Output path with the target extension (e.g., 'image.webp').
    """
    err = _check_pillow()
    if err:
        return err
    try:
        img = Image.open(input_path)
        ext = os.path.splitext(output_path)[1].lower()

        # JPEG doesn't support transparency — convert to RGB
        if ext in (".jpg", ".jpeg") and img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        img.save(output_path)
        in_size = os.path.getsize(input_path) / 1024
        out_size = os.path.getsize(output_path) / 1024
        in_fmt = os.path.splitext(input_path)[1].upper()
        out_fmt = ext.upper()
        return (
            f"✅ Converted {in_fmt} → {out_fmt}\n"
            f"Input:  {in_size:.1f} KB\n"
            f"Output: {out_size:.1f} KB\n"
            f"Saved:  {output_path}"
        )
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def compress_image(input_path: str, output_path: str, quality: int = 70) -> str:
    """Compresses an image to reduce its file size with adjustable quality.

    Args:
        input_path: Path to the source image.
        output_path: Path to save the compressed image (use .jpg for best compression).
        quality: Compression quality 1-95 (lower = smaller file, default 70).
    """
    err = _check_pillow()
    if err:
        return err
    try:
        quality = max(1, min(95, quality))
        img = Image.open(input_path)

        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        img.save(output_path, optimize=True, quality=quality)
        in_size = os.path.getsize(input_path) / 1024
        out_size = os.path.getsize(output_path) / 1024
        saved_pct = (1 - out_size / in_size) * 100 if in_size > 0 else 0
        return (
            f"✅ Image compressed\n"
            f"Original: {in_size:.1f} KB\n"
            f"Compressed: {out_size:.1f} KB ({saved_pct:.1f}% smaller)\n"
            f"Quality: {quality}/95\n"
            f"Saved: {output_path}"
        )
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def crop_image(
    input_path: str,
    output_path: str,
    left: int = 0,
    top: int = 0,
    right: int = 0,
    bottom: int = 0,
) -> str:
    """Crops an image to the specified pixel coordinates.

    Args:
        input_path: Path to the source image.
        output_path: Path to save the cropped image.
        left: Left edge in pixels.
        top: Top edge in pixels.
        right: Right edge in pixels (0 = image width).
        bottom: Bottom edge in pixels (0 = image height).
    """
    err = _check_pillow()
    if err:
        return err
    try:
        img = Image.open(input_path)
        w, h = img.size
        r = right if right > 0 else w
        b = bottom if bottom > 0 else h
        cropped = img.crop((left, top, r, b))
        cropped.save(output_path)
        cw, ch = cropped.size
        return (
            f"✅ Image cropped\n"
            f"Original: {w}×{h}\n"
            f"Cropped:  {cw}×{ch}\n"
            f"Region:   ({left},{top}) → ({r},{b})\n"
            f"Saved:    {output_path}"
        )
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def add_watermark(
    input_path: str,
    output_path: str,
    text: str,
    position: str = "bottom-right",
    opacity: int = 128,
    font_size: int = 36,
) -> str:
    """Adds a semi-transparent text watermark to an image.

    Args:
        input_path: Path to the source image.
        output_path: Path to save the watermarked image.
        text: Watermark text (e.g., '© 2025 My Name').
        position: 'top-left', 'top-right', 'bottom-left', 'bottom-right', 'center' (default 'bottom-right').
        opacity: Watermark transparency 0 (invisible) to 255 (solid), default 128.
        font_size: Font size in points (default 36).
    """
    err = _check_pillow()
    if err:
        return err
    try:
        img = Image.open(input_path).convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Try to use a system font, fall back to default
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        margin = 15
        w, h = img.size

        pos_map = {
            "top-left": (margin, margin),
            "top-right": (w - tw - margin, margin),
            "bottom-left": (margin, h - th - margin),
            "bottom-right": (w - tw - margin, h - th - margin),
            "center": ((w - tw) // 2, (h - th) // 2),
        }
        xy = pos_map.get(position, pos_map["bottom-right"])

        # Draw shadow then text
        draw.text((xy[0] + 2, xy[1] + 2), text, font=font, fill=(0, 0, 0, opacity))
        draw.text(xy, text, font=font, fill=(255, 255, 255, opacity))

        combined = Image.alpha_composite(img, overlay)
        combined = combined.convert("RGB") if output_path.lower().endswith((".jpg", ".jpeg")) else combined
        combined.save(output_path)
        return f"✅ Watermark added\nText: '{text}'\nPosition: {position}\nSaved: {output_path}"
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def generate_qr_code(data: str, output_path: str, size: int = 10, border: int = 4) -> str:
    """Generates a QR code image from text or a URL.

    Args:
        data: Text or URL to encode in the QR code.
        output_path: Path to save the QR code image (e.g., 'qr_code.png').
        size: Box size in pixels per module (default 10).
        border: Border thickness in boxes (default 4).
    """
    if not HAS_QRCODE:
        return "❌ qrcode not installed. Run: pip install qrcode[pil]"
    try:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(output_path)
        file_size = os.path.getsize(output_path) / 1024
        return (
            f"✅ QR Code generated\n"
            f"Data:   {data[:60]}{'...' if len(data) > 60 else ''}\n"
            f"Size:   {img.size[0]}×{img.size[1]} px\n"
            f"Saved:  {output_path} ({file_size:.1f} KB)"
        )
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def image_to_text_ocr(image_path: str) -> str:
    """Extracts text from an image using OCR (Optical Character Recognition).

    Requires: pip install pytesseract AND Tesseract OCR installed on your system.
    Download Tesseract: https://github.com/tesseract-ocr/tesseract

    Args:
        image_path: Path to the image file containing text.
    """
    if not HAS_TESSERACT:
        return (
            "❌ pytesseract not installed. Run: pip install pytesseract\n"
            "Also install Tesseract OCR from: https://github.com/tesseract-ocr/tesseract"
        )
    if not HAS_PILLOW:
        return "❌ Pillow not installed. Run: pip install Pillow"
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        if not text.strip():
            return "⚠️  No text detected in the image."
        return f"📝 Extracted Text:\n{'─' * 40}\n{text.strip()}"
    except Exception as e:
        return f"❌ Error: {e}"


@tool
def get_image_info(image_path: str) -> str:
    """Returns detailed information about an image file.

    Args:
        image_path: Path to the image file.
    """
    err = _check_pillow()
    if err:
        return err
    try:
        if not os.path.exists(image_path):
            return f"❌ File not found: {image_path}"
        img = Image.open(image_path)
        size_kb = os.path.getsize(image_path) / 1024
        return (
            f"🖼️  Image Info: {os.path.basename(image_path)}\n"
            f"{'─' * 40}\n"
            f"Format:     {img.format}\n"
            f"Mode:       {img.mode} (color space)\n"
            f"Dimensions: {img.width}×{img.height} px\n"
            f"File Size:  {size_kb:.2f} KB\n"
            f"Megapixels: {(img.width * img.height) / 1_000_000:.2f} MP"
        )
    except Exception as e:
        return f"❌ Error: {e}"
