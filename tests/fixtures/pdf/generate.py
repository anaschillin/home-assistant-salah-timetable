"""Generate original, deterministic MIT-licensed PDF layout fixtures.

No real mosque timetable is represented. Times are synthetic test data.
Run with Python from any directory; no PDF-generation dependency is required.
"""

from pathlib import Path


def make_pdf(pages: list[list[str]]) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    ]
    page_refs = []
    for lines in pages:
        page_id = len(objects) + 1
        content_id = page_id + 1
        page_refs.append(f"{page_id} 0 R")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 1000 800] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
        escaped = [
            line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            for line in lines
        ]
        commands = (
            "BT /F1 10 Tf 30 760 Td 16 TL\n"
            + "\n".join(f"({line}) Tj T*" for line in escaped)
            + "\nET"
        )
        stream = commands.encode("latin-1")
        objects.append(
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        )
    objects[1] = (
        f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(pages)} >>".encode()
    )
    result = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(result)
    result.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode())
    result.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(result)


if __name__ == "__main__":
    root = Path(__file__).parent
    header = "Date | Fajr Begin | Fajr Jamaat | Sunrise | Jumuah"
    annual = make_pdf(
        [
            [
                "Salah Timetable",
                "Mosque: Synthetic Example",
                "Year 2026",
                header,
                "2026-01-01 | 06:15 | 06:45 | 08:10 |",
                '2026-01-02 | 06:16 | " | 08:11 | 13:00;14:00',
            ],
            [
                "Salah Timetable",
                "Year 2026",
                header,
                "2026-01-03 | 06:17 | 06:45 | 08:12 |",
            ],
        ]
    )
    (root / "sample_table.pdf").write_bytes(annual)
    (root / "unsupported_layout.pdf").write_bytes(
        make_pdf(
            [
                [
                    "Prayer times",
                    "Fajr 6:15am",
                    "This is an unsupported free-form layout.",
                ]
            ]
        )
    )
    (root / "sample_table.expected.csv").write_text(
        'Date,Fajr Begin,Fajr Jamaat,Sunrise,Jumuah\n2026-01-01,06:15,06:45,08:10,\n2026-01-02,06:16,"""",08:11,13:00;14:00\n2026-01-03,06:17,06:45,08:12,\n'
    )
