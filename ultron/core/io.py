"""
core/io.py — Centralized filesystem utilities.

Keeps models.py dependency-free by owning all file read/write logic.
"""


def read_text(filepath):
    """
    Read a text file safely with BOM stripping and LF normalization.

    Raises:
        OSError: if the file cannot be opened.
        UnicodeDecodeError: if encoding fails (should not happen with utf-8-sig).
    """
    with open(filepath, encoding="utf-8-sig") as fh:
        return fh.read().replace("\r\n", "\n").replace("\r", "\n")
