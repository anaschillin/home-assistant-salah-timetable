"""Isolated, resource-limited PDF text extraction worker.

This file is launched with the active interpreter and -I. It must not import HA or
integration modules: parsing an uploaded document never needs HA configuration or
injected credentials. stdout is a bounded JSON result; diagnostics are generic.
"""

import io
import json
import resource
import sys

# Keep in sync with import_model.MAX_PDF_BYTES; this isolated script intentionally
# imports no integration modules. The actual-worker tests exercise the boundary.
MAX_PDF_BYTES = 4 * 1024 * 1024
MAX_PAGES = 16
MAX_TEXT_BYTES = 256 * 1024
MAX_PAGE_STREAM_BYTES = 2 * 1024 * 1024


def main() -> int:
    """Read bounded stdin, extract text under hard process resource limits."""
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (4, 5))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    import pypdf
    from pypdf import filters

    # pypdf has explicit decompression guards. Tighten them before touching input;
    # the process memory/CPU limits remain a second bound for malformed object graphs.
    for name in (
        "FLATE_MAX_BUFFER_SIZE",
        "JBIG2_MAX_OUTPUT_LENGTH",
        "LZW_MAX_OUTPUT_LENGTH",
        "MAX_ARRAY_BASED_STREAM_OUTPUT_LENGTH",
        "MAX_DECLARED_STREAM_LENGTH",
        "RUN_LENGTH_MAX_OUTPUT_LENGTH",
        "ZLIB_MAX_OUTPUT_LENGTH",
    ):
        setattr(filters, name, 8 * 1024 * 1024)
    filters.FLATE_MAX_COLUMNS = 1024
    filters.FLATE_MAX_ROW_LENGTH = 16 * 1024
    filters.ZLIB_MAX_RECOVERY_INPUT_LENGTH = MAX_PDF_BYTES

    content = sys.stdin.buffer.read(MAX_PDF_BYTES + 1)
    if not content.startswith(b"%PDF-") or len(content) > MAX_PDF_BYTES:
        return 2
    reader = pypdf.PdfReader(io.BytesIO(content), strict=True)
    if reader.is_encrypted or not 1 <= len(reader.pages) <= MAX_PAGES:
        return 2
    total = 0
    pages = []
    for page in reader.pages:
        stream = page.get_contents()
        if stream is None or len(stream.get_data()) > MAX_PAGE_STREAM_BYTES:
            return 2
        text = page.extract_text()
        if not isinstance(text, str) or not text.strip():
            return 2
        total += len(text.encode("utf-8"))
        if total > MAX_TEXT_BYTES:
            return 2
        pages.append(text)
    sys.stdout.write(json.dumps({"pages": pages}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        # Never emit PDF text, filenames, object content, or interpreter paths.
        code = 2
    raise SystemExit(code)
