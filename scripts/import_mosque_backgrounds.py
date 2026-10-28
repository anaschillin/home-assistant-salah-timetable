"""Download verified Unsplash free photos and prepare optimised bundled backgrounds.

This is a maintainer-only reproducible asset import. No runtime network access.
Only the explicitly reviewed source pages/photographs below are permitted.
"""

import hashlib
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "custom_components/salah_timetable/frontend"
TARGET = FRONTEND / "backgrounds"
INVENTORY = ROOT / "docs/asset-provenance.json"
MANIFEST = FRONTEND / "mosque-backgrounds.js"
CREDITS = ROOT / "docs/mosque-background-credits.md"
LICENSE_URL = "https://unsplash.com/license"
MAX_DOWNLOAD_BYTES = 15_000_000
MAX_WEBP_BYTES = 250_000

PHOTOS = [
  {
    "id": "masjid-al-haram",
    "name": "Masjid al-Haram",
    "country": "Saudi Arabia",
    "photographer": "Ishan",
    "page": "https://unsplash.com/photos/kaaba-in-mecca-with-crowd-66Tu10CxYY0",
    "photo": "photo-1592326871020-04f58c1a52f3",
    "position": "center"
  },
  {
    "id": "masjid-an-nabawi",
    "name": "Masjid an-Nabawi",
    "country": "Saudi Arabia",
    "photographer": "Haidan",
    "page": "https://unsplash.com/photos/al-masjid-an-nabawi-mosque-in-medina-Qec3HPaHWTI",
    "photo": "photo-1605976528013-638e49b6599f",
    "position": "center"
  },
  {
    "id": "sheikh-zayed-grand-mosque",
    "name": "Sheikh Zayed Grand Mosque",
    "country": "United Arab Emirates",
    "photographer": "David Rodrigo",
    "page": "https://unsplash.com/photos/sheikh-zayed-grand-mosque-in-abu-dhabi-kZ1zThg6G40",
    "photo": "photo-1512632578888-169bbbc64f33",
    "position": "center"
  },
  {
    "id": "sultan-ahmed-mosque",
    "name": "Sultan Ahmed Mosque",
    "country": "Türkiye",
    "photographer": "Max van den Oetelaar",
    "page": "https://unsplash.com/photos/a-walkway-leading-to-a-large-building-with-many-spires-bs1Nu9x7bNc",
    "photo": "photo-1649333195003-18c47d64ed18",
    "position": "center"
  },
  {
    "id": "badshahi-mosque",
    "name": "Badshahi Mosque",
    "country": "Pakistan",
    "photographer": "Sohail Chaudhry",
    "page": "https://unsplash.com/photos/brown-concrete-building-under-cloudy-sky-during-daytime-ayAl0D6mxHM",
    "photo": "photo-1617128072203-310a93722ad8",
    "position": "center"
  },
  {
    "id": "hassan-ii-mosque",
    "name": "Hassan II Mosque",
    "country": "Morocco",
    "photographer": "Ajmal MK",
    "page": "https://unsplash.com/photos/green-and-white-concrete-building-under-blue-sky-during-daytime-EJSGszHvVGI",
    "photo": "photo-1590654643716-2eaca12ce6ff",
    "position": "center"
  },
  {
    "id": "great-mosque-of-kairouan",
    "name": "Great Mosque of Kairouan",
    "country": "Tunisia",
    "photographer": "Malek Boukhris",
    "page": "https://unsplash.com/photos/great-mosque-of-kairouan-in-tunisia-0-Sn6xvf3BM",
    "photo": "photo-1577908754561-dfcdc9649ddf",
    "position": "center"
  },
  {
    "id": "baiturrahman-grand-mosque",
    "name": "Baiturrahman Grand Mosque",
    "country": "Indonesia",
    "photographer": "Sangga Rima Roman Selia",
    "page": "https://unsplash.com/photos/white-concrete-building-during-daytime-2lbcJYnxvqw",
    "photo": "photo-1591019401711-0f983e4af346",
    "position": "center"
  }
]


def fetch_image(photo: dict) -> bytes:
    """Fetch a reviewed, immutable Unsplash photo ID, never an arbitrary URL."""
    url = (
        f"https://images.unsplash.com/{photo['photo']}"
        "?fit=max&w=1800&fm=jpg&q=85"
    )
    request = Request(url, headers={"User-Agent": "SalahTimetableAssetImport/1.0"})
    with urlopen(request, timeout=40) as response:
        data = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise ValueError(f"Image exceeds download size limit: {photo['id']}")
    return data


def optimise(data: bytes) -> bytes:
    """Convert to a legible, bounded WebP image with no EXIF metadata."""
    Image.MAX_IMAGE_PIXELS = 30_000_000
    with Image.open(io.BytesIO(data)) as original:
        original.verify()
    with Image.open(io.BytesIO(data)) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
    image.thumbnail((1600, 1100), Image.Resampling.LANCZOS)
    for scale in (1, 0.86, 0.74):
        candidate = image.copy()
        if scale != 1:
            candidate.thumbnail(
                (int(image.width * scale), int(image.height * scale)),
                Image.Resampling.LANCZOS,
            )
        for quality in (72, 64, 56, 48):
            output = io.BytesIO()
            candidate.save(output, format="WEBP", quality=quality, method=6)
            webp = output.getvalue()
            if len(webp) <= MAX_WEBP_BYTES:
                return webp
    raise ValueError("Unable to encode image within 250 KB limit")


def update_manifest(items: list[dict]) -> None:
    """Preserve the separately maintained rotation helper."""
    existing = MANIFEST.read_text(encoding="utf-8")
    helper = existing.split("/** Stable day-based rotation", maxsplit=1)[1]
    body = json.dumps(items, ensure_ascii=False, indent=2)
    MANIFEST.write_text(
        "/** Reviewed Unsplash License photographs, bundled for offline use. */\n"
        f"export const MOSQUE_BACKGROUNDS = Object.freeze({body});\n\n"
        "/** Stable day-based rotation" + helper,
        encoding="utf-8",
    )


def update_provenance(items: list[dict], checksums: dict[str, str]) -> None:
    """Account for every new binary in the repository asset audit."""
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    entries = {entry["path"]: entry for entry in inventory["assets"]}
    for item in items:
        path = "custom_components/salah_timetable/frontend" + item["path"].removeprefix("/salah_timetable")
        entries[path] = {
            "path": path,
            "rights": "permission_documented",
            "owner": item["photographer"],
            "basis": "Free photograph under the Unsplash License; converted to WebP and resized",
            "evidence": item["source_url"],
            "sha256": checksums[item["id"]],
        }
    inventory["assets"] = sorted(entries.values(), key=lambda entry: entry["path"])
    INVENTORY.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    items = []
    checksums = {}
    for photo in PHOTOS:
        webp = optimise(fetch_image(photo))
        file = TARGET / f"{photo['id']}.webp"
        file.write_bytes(webp)
        checksums[photo["id"]] = hashlib.sha256(webp).hexdigest()
        items.append(
            {
                "id": photo["id"],
                "name": photo["name"],
                "country": photo["country"],
                "photographer": photo["photographer"],
                "source_url": photo["page"],
                "license_url": LICENSE_URL,
                "path": f"/salah_timetable/backgrounds/{photo['id']}.webp",
                "position": photo["position"],
            }
        )
        print(f"{file.relative_to(ROOT)}: {len(webp)} bytes")
    update_manifest(items)
    update_provenance(items, checksums)
    rows = [
        "# Mosque photograph credits",
        "",
        "Photographs resized and converted to WebP for offline Home Assistant use.",
        "All photographs were marked 'Free to use under the Unsplash License' on their source pages.",
        f"License: {LICENSE_URL}",
        "",
        "| Mosque | Photographer | Original photograph |",
        "|---|---|---|",
    ]
    for photo in PHOTOS:
        rows.append(
            f"| {photo['name']} ({photo['country']}) | {photo['photographer']} | [Unsplash]({photo['page']}) |"
        )
    CREDITS.write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
