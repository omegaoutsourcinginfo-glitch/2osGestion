"""Upload validators: extension + magic-byte (content) checks."""

from __future__ import annotations

from typing import BinaryIO

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


def _read_header(file_obj: BinaryIO, size: int = 32) -> bytes:
    pos = file_obj.tell() if hasattr(file_obj, "tell") else None
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    header = file_obj.read(size) or b""
    if hasattr(file_obj, "seek") and pos is not None:
        file_obj.seek(pos)
    return header


def _is_zip_container(header: bytes) -> bool:
    # DOCX / XLSX / PPTX are ZIP (PK..)
    return header.startswith(b"PK")


def _is_ole_container(header: bytes) -> bool:
    # Legacy DOC / XLS
    return header.startswith(b"\xd0\xcf\x11\xe0")


def _matches_extension(header: bytes, ext: str) -> bool:
    ext = ext.lower().lstrip(".")
    if ext == "pdf":
        return header.startswith(b"%PDF")
    if ext in {"jpg", "jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    if ext == "png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if ext == "gif":
        return header.startswith(b"GIF87a") or header.startswith(b"GIF89a")
    if ext == "webp":
        return header.startswith(b"RIFF") and b"WEBP" in header[:16]
    if ext == "doc":
        return _is_ole_container(header)
    if ext == "docx":
        return _is_zip_container(header)
    if ext == "xls":
        return _is_ole_container(header)
    if ext == "xlsx":
        return _is_zip_container(header)
    if ext == "dwg":
        # AutoCAD DWG versions often start with "AC10.."
        return header.startswith(b"AC")
    return False


@deconstructible
class FileSignatureValidator:
    """
    Reject files whose content does not match the declared extension.

    Complements FileExtensionValidator (name-only) with magic-byte checks.
    """

    message = (
        "Le contenu du fichier ne correspond pas à l'extension « %(ext)s ». "
        "Fichier rejeté."
    )
    code = "invalid_file_signature"

    def __init__(self, allowed_extensions: list[str] | None = None):
        self.allowed_extensions = [
            e.lower().lstrip(".") for e in (allowed_extensions or [])
        ]

    def __call__(self, value):
        if not value:
            return
        name = getattr(value, "name", "") or ""
        if "." not in name:
            raise ValidationError(
                self.message,
                code=self.code,
                params={"ext": "?"},
            )
        ext = name.rsplit(".", 1)[-1].lower()
        if self.allowed_extensions and ext not in self.allowed_extensions:
            # Let FileExtensionValidator report the extension error.
            return
        try:
            header = _read_header(value, 32)
        except OSError as exc:
            raise ValidationError(
                "Impossible de lire le fichier téléversé.",
                code=self.code,
            ) from exc
        if not header or not _matches_extension(header, ext):
            raise ValidationError(
                self.message,
                code=self.code,
                params={"ext": ext},
            )

    def __eq__(self, other):
        return (
            isinstance(other, FileSignatureValidator)
            and self.allowed_extensions == other.allowed_extensions
        )


def file_validators(extensions: list[str]) -> list:
    """Extension check + content signature check for the same allow-list."""
    from django.core.validators import FileExtensionValidator

    return [
        FileExtensionValidator(extensions),
        FileSignatureValidator(extensions),
    ]
