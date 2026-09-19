"""Write a Teams submission copy of a Markdown laboratory report.

The source report and its local image files are left unchanged. The command
writes ``submission/REPORT.md`` beside the source report, replacing local
Markdown image paths with base64 ``data:`` URIs so Microsoft Teams can render
the file as a single attachment.
"""

from __future__ import annotations

import base64
import io
import mimetypes
import re
from pathlib import Path

from PIL import Image, ImageOps

from .workflow import WorkflowError

IMAGE_PATTERN = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<target>[^)]+)\)")
REMOTE_TARGET_PREFIXES = ("data:", "http://", "https://")
JPEG_SUFFIXES = {".jpg", ".jpeg"}
PNG_SUFFIXES = {".png"}
DEFAULT_MAX_WIDTH = 800
DEFAULT_MAX_HEIGHT = 600
SUBMISSION_DIRNAME = "submission"
SUBMISSION_FILENAME = "REPORT.md"


def prepare_report(
    report_path: Path,
    output_path: Path | None = None,
    max_width: int = DEFAULT_MAX_WIDTH,
    max_height: int = DEFAULT_MAX_HEIGHT,
) -> tuple[Path, int]:
    """Write a self-contained submission copy and return its path and image count."""
    source = report_path.resolve()
    if not source.is_file():
        raise WorkflowError(f"Report not found: {source}")

    destination = (
        output_path.resolve()
        if output_path is not None
        else source.parent / SUBMISSION_DIRNAME / SUBMISSION_FILENAME
    )
    if destination == source:
        raise WorkflowError("The submission copy must not overwrite the source report.")

    report_text = source.read_text(encoding="utf-8")
    embedded, image_count = _embed_local_images(
        report_text,
        report_path=source,
        max_width=max_width,
        max_height=max_height,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(embedded, encoding="utf-8")
    return destination, image_count


def _embed_local_images(
    report_text: str,
    report_path: Path,
    max_width: int,
    max_height: int,
) -> tuple[str, int]:
    encoded_images: dict[Path, str] = {}

    def replace_image(match: re.Match[str]) -> str:
        alt_text = match.group("alt")
        target = _resolve_markdown_target(match.group("target"))
        if _is_remote_markdown_target(target):
            return match.group(0)

        image_path = _resolve_local_image(report_path, target)
        if image_path not in encoded_images:
            encoded_images[image_path] = _file_to_data_uri(
                image_path, max_width=max_width, max_height=max_height
            )
        return f"![{alt_text}]({encoded_images[image_path]})"

    rewritten = IMAGE_PATTERN.sub(replace_image, report_text)
    return rewritten, len(encoded_images)


def _resolve_markdown_target(target: str) -> str:
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        return target[1:-1].strip()
    if " " in target and not target.startswith("data:"):
        return target.split(" ", 1)[0]
    return target


def _is_remote_markdown_target(target: str) -> bool:
    return target.startswith(REMOTE_TARGET_PREFIXES)


def _resolve_local_image(report_path: Path, target: str) -> Path:
    report_dir = report_path.parent.resolve()
    image_path = (report_dir / target).resolve()
    try:
        image_path.relative_to(report_dir)
    except ValueError as exc:
        raise WorkflowError(
            f"Image path {target} resolves outside the report directory: {image_path}"
        ) from exc
    if not image_path.is_file():
        raise WorkflowError(f"Image referenced in the report was not found: {image_path}")
    return image_path


def _file_to_data_uri(path: Path, max_width: int, max_height: int) -> str:
    suffix = path.suffix.lower()
    with Image.open(path) as original:
        width, height = original.size
        if width <= max_width and height <= max_height:
            payload = path.read_bytes()
            mime_type = _mime_type(path, suffix)
            encoded = base64.b64encode(payload).decode("ascii")
            return f"data:{mime_type};base64,{encoded}"

        image = ImageOps.exif_transpose(original)
        image = _normalize_image(image, suffix)
        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        if suffix in JPEG_SUFFIXES:
            image.save(buffer, format="JPEG", quality=82, optimize=True, progressive=True)
            mime_type = "image/jpeg"
        else:
            image.save(buffer, format="PNG", optimize=True)
            mime_type = "image/png"
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"


def _normalize_image(image: Image.Image, suffix: str) -> Image.Image:
    if suffix in JPEG_SUFFIXES:
        if image.mode not in ("RGB", "L"):
            background = Image.new("RGB", image.size, (255, 255, 255))
            alpha_image = image.convert("RGBA")
            background.paste(alpha_image, mask=alpha_image.getchannel("A"))
            return background
        if image.mode == "L":
            return image.convert("RGB")
        return image
    if suffix in PNG_SUFFIXES and image.mode == "P":
        return image.convert("RGBA")
    return image


def _mime_type(path: Path, suffix: str) -> str:
    mime_type, _ = mimetypes.guess_type(path.name)
    if mime_type:
        return mime_type
    if suffix in JPEG_SUFFIXES:
        return "image/jpeg"
    if suffix in PNG_SUFFIXES:
        return "image/png"
    return "application/octet-stream"
