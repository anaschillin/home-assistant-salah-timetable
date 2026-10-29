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
LICENSE_URL = "https://unsplash.com/license"

PHOTOS = [
    {
        "id": "masjid-al-haram",
        "name": "Masjid al-Haram",
        "country": "Saudi Arabia",
        "photographer": "Ishan",
        "page": "https://unsplash.com/photos/kaaba-in-mecca-with-crowd-66Tu10CxYY0",
        "photo": "photo-1592326871020-04f58c1a52f3",
        "position": "center",
    },
    {
        "id": "masjid-an-nabawi",
        "name": "Masjid an-Nabawi",
        "country": "Saudi Arabia",
        "photographer": "Haidan",
        "page": "https://unsplash.com/photos/al-masjid-an-nabawi-mosque-in-medina-Qec3HPaHWTI",
        "photo": "photo-1605976528013-638e49b6599f",
        "position": "center",
    },
    {
        "id": "sheikh-zayed-grand-mosque",
        "name": "Sheikh Zayed Grand Mosque",
        "country": "United Arab Emirates",
        "photographer": "David Rodrigo",
        "page": "https://unsplash.com/photos/sheikh-zayed-grand-mosque-in-abu-dhabi-kZ1zThg6G40",
        "photo": "photo-1512632578888-169bbbc64f33",
        "position": "center",
    },
    {
        "id": "sultan-ahmed-mosque",
        "name": "Sultan Ahmed Mosque",
        "country": "Türkiye",
        "photographer": "Max van den Oetelaar",
        "page": "https://unsplash.com/photos/a-walkway-leading-to-a-large-building-with-many-spires-bs1Nu9x7bNc",
        "photo": "photo-1649333195003-18c47d64ed18",
        "position": "center",
    },
    {
        "id": "badshahi-mosque",
        "name": "Badshahi Mosque",
        "country": "Pakistan",
        "photographer": "Sohail Chaudhry",
        "page": "https://unsplash.com/photos/brown-concrete-building-under-cloudy-sky-during-daytime-ayAl0D6mxHM",
        "photo": "photo-1617128072203-310a93722ad8",
        "position": "center",
    },
    {
        "id": "hassan-ii-mosque",
        "name": "Hassan II Mosque",
        "country": "Morocco",
        "photographer": "Ajmal MK",
        "page": "https://unsplash.com/photos/green-and-white-concrete-building-under-blue-sky-during-daytime-EJSGszHvVGI",
        "photo": "photo-1590654643716-2eaca12ce6ff",
        "position": "center",
    },
    {
        "id": "great-mosque-of-kairouan",
        "name": "Great Mosque of Kairouan",
        "country": "Tunisia",
        "photographer": "Malek Boukhris",
        "page": "https://unsplash.com/photos/great-mosque-of-kairouan-in-tunisia-0-Sn6xvf3BM",
        "photo": "photo-1577908754561-dfcdc9649ddf",
        "position": "center",
    },
    {
        "id": "baiturrahman-grand-mosque",
        "name": "Baiturrahman Grand Mosque",
        "country": "Indonesia",
        "photographer": "Sangga Rima Roman Selia",
        "page": "https://unsplash.com/photos/white-concrete-building-during-daytime-2lbcJYnxvqw",
        "photo": "photo-1591019401711-0f983e4af346",
        "position": "center",
    },
    {
        "id": "faisal-mosque",
        "name": "Shah Faisal Mosque",
        "country": "Pakistan",
        "photographer": "Faisal Mehmood",
        "page": "https://unsplash.com/photos/a-building-with-a-tower-OgP5pfVRdhk",
        "photo": "photo-1664185494321-37a1fcf6e04d",
        "position": "center",
    },
    {
        "id": "wazir-khan-mosque",
        "name": "Wazir Khan Mosque",
        "country": "Pakistan",
        "photographer": "Arooba Arif",
        "page": "https://unsplash.com/photos/a-view-of-a-building-through-an-archway-LbRCic9i5JY",
        "photo": "photo-1653248388588-208e466ec0b0",
        "position": "center",
    },
    {
        "id": "suleymaniye-mosque",
        "name": "Süleymaniye Mosque",
        "country": "Türkiye",
        "photographer": "ekrem osmanoglu",
        "page": "https://unsplash.com/photos/suleymaniye-mosque-in-istanbul-turkey-ukXyJKPg94s",
        "photo": "photo-1577890300102-d01f7e6b010f",
        "position": "center",
    },
    {
        "id": "hagia-sophia-grand-mosque",
        "name": "Hagia Sophia Grand Mosque",
        "country": "Türkiye",
        "photographer": "Dmitry Limonov",
        "page": "https://unsplash.com/photos/a-large-building-with-hagia-sophia-JC-nWdz_tSI",
        "photo": "photo-1667816405141-197c14c30738",
        "position": "center",
    },
    {
        "id": "al-azhar-mosque",
        "name": "Al-Azhar Mosque",
        "country": "Egypt",
        "photographer": "Seif Amr",
        "page": "https://unsplash.com/photos/people-walking-near-white-concrete-building-during-daytime-vjv3xVeDguA",
        "photo": "photo-1618224237039-0f55d9f40c1c",
        "position": "center",
    },
    {
        "id": "muhammad-ali-mosque",
        "name": "Muhammad Ali Mosque",
        "country": "Egypt",
        "photographer": "Martijn Vonk",
        "page": "https://unsplash.com/photos/a-picture-of-a-very-large-building-with-many-spires-dHQBr-oNodQ",
        "photo": "photo-1738511582259-470641311732",
        "position": "center",
    },
    {
        "id": "koutoubia-mosque",
        "name": "Koutoubia Mosque",
        "country": "Morocco",
        "photographer": "gemmmm 🖤",
        "page": "https://unsplash.com/photos/brown-concrete-building-under-blue-sky-during-daytime-tSy3SRzYJu4",
        "photo": "photo-1585336897192-540964ec47f2",
        "position": "center",
    },
    {
        "id": "mosque-cathedral-cordoba",
        "name": "Historic Mosque-Cathedral of Córdoba",
        "country": "Spain",
        "photographer": "Alexandra Tran",
        "page": "https://unsplash.com/photos/the-inside-of-a-building-with-columns-and-arches-rvE_jTiejVc",
        "photo": "photo-1632904080322-e71e16a5987f",
        "position": "center",
    },
    {
        "id": "jama-masjid-delhi",
        "name": "Jama Masjid, Delhi",
        "country": "India",
        "photographer": "Naveed Ahmed",
        "page": "https://unsplash.com/photos/people-outside-mosque-XIdBO7BtZhY",
        "photo": "photo-1577214382660-a347368c7325",
        "position": "center",
    },
    {
        "id": "omar-ali-saifuddien-mosque",
        "name": "Sultan Omar Ali Saifuddien Mosque",
        "country": "Brunei",
        "photographer": "Jimmy Whitson",
        "page": "https://unsplash.com/photos/golden-domed-mosque-with-minarets-at-sunrise-KNIIpxvwPaM",
        "photo": "photo-1777858344918-ee54fb902d23",
        "position": "center",
    },
    {
        "id": "national-mosque-malaysia",
        "name": "National Mosque of Malaysia (Masjid Negara)",
        "country": "Malaysia",
        "photographer": "The Simple Travel",
        "page": "https://unsplash.com/photos/a-fountain-with-a-clock-tower-in-the-background-2vwnPAk47Gg",
        "photo": "photo-1635528266606-2a40bdc071d9",
        "position": "center",
    },
    {
        "id": "al-qibli-mosque",
        "name": "Al-Qibli Mosque (Al-Aqsa compound)",
        "country": "Jerusalem",
        "photographer": "Cole Keister",
        "page": "https://unsplash.com/photos/al-aqsa-mosque-behind-blurred-flowers-PQnkV6-iZMw",
        "photo": "photo-1542317803-0fc679478393",
        "position": "center",
    },
]


def fetch_image(photo: dict) -> bytes:
    """Fetch a reviewed, immutable Unsplash photo ID, never an arbitrary URL."""
    url = f"https://images.unsplash.com/{photo['photo']}?fit=max&w=1800&fm=jpg&q=85"
    request = Request(url, headers={"User-Agent": "SalahTimetableAssetImport/1.0"})
    with urlopen(request, timeout=40) as response:
        data = response.read()
    return data


def optimise(data: bytes) -> bytes:
    """Encode the full-resolution source as genuinely lossless WebP."""
    with Image.open(io.BytesIO(data)) as original:
        original.verify()
    with Image.open(io.BytesIO(data)) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
    output = io.BytesIO()
    image.save(output, format="WEBP", lossless=True, method=6, exact=True)
    return output.getvalue()


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
        path = "custom_components/salah_timetable/frontend" + item["path"].removeprefix(
            "/salah_timetable"
        )
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
        file = TARGET / f"{photo['id']}.webp"
        if file.is_file():
            # Preserve previously bundled assets until their sources are replaced.
            webp = file.read_bytes()
            if webp[:4] != b"RIFF" or webp[8:12] != b"WEBP":
                raise ValueError(f"Invalid existing background: {photo['id']}")
        else:
            webp = optimise(fetch_image(photo))
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
                "source_photo_id": photo["photo"],
            }
        )
        print(f"{file.relative_to(ROOT)}: {len(webp)} bytes")
    update_manifest(items)
    update_provenance(items, checksums)


if __name__ == "__main__":
    main()
