/** Reviewed Unsplash License photographs, bundled for offline use. */
export const MOSQUE_BACKGROUNDS = Object.freeze([
  {
    "id": "masjid-al-haram",
    "name": "Masjid al-Haram",
    "country": "Saudi Arabia",
    "photographer": "Ishan",
    "source_url": "https://unsplash.com/photos/kaaba-in-mecca-with-crowd-66Tu10CxYY0",
    "license_url": "https://unsplash.com/license",
    "path": "/salah_timetable/backgrounds/masjid-al-haram.webp",
    "position": "center"
  },
  {
    "id": "masjid-an-nabawi",
    "name": "Masjid an-Nabawi",
    "country": "Saudi Arabia",
    "photographer": "Haidan",
    "source_url": "https://unsplash.com/photos/al-masjid-an-nabawi-mosque-in-medina-Qec3HPaHWTI",
    "license_url": "https://unsplash.com/license",
    "path": "/salah_timetable/backgrounds/masjid-an-nabawi.webp",
    "position": "center"
  },
  {
    "id": "sheikh-zayed-grand-mosque",
    "name": "Sheikh Zayed Grand Mosque",
    "country": "United Arab Emirates",
    "photographer": "David Rodrigo",
    "source_url": "https://unsplash.com/photos/sheikh-zayed-grand-mosque-in-abu-dhabi-kZ1zThg6G40",
    "license_url": "https://unsplash.com/license",
    "path": "/salah_timetable/backgrounds/sheikh-zayed-grand-mosque.webp",
    "position": "center"
  },
  {
    "id": "sultan-ahmed-mosque",
    "name": "Sultan Ahmed Mosque",
    "country": "Türkiye",
    "photographer": "Max van den Oetelaar",
    "source_url": "https://unsplash.com/photos/a-walkway-leading-to-a-large-building-with-many-spires-bs1Nu9x7bNc",
    "license_url": "https://unsplash.com/license",
    "path": "/salah_timetable/backgrounds/sultan-ahmed-mosque.webp",
    "position": "center"
  },
  {
    "id": "badshahi-mosque",
    "name": "Badshahi Mosque",
    "country": "Pakistan",
    "photographer": "Sohail Chaudhry",
    "source_url": "https://unsplash.com/photos/brown-concrete-building-under-cloudy-sky-during-daytime-ayAl0D6mxHM",
    "license_url": "https://unsplash.com/license",
    "path": "/salah_timetable/backgrounds/badshahi-mosque.webp",
    "position": "center"
  },
  {
    "id": "hassan-ii-mosque",
    "name": "Hassan II Mosque",
    "country": "Morocco",
    "photographer": "Ajmal MK",
    "source_url": "https://unsplash.com/photos/green-and-white-concrete-building-under-blue-sky-during-daytime-EJSGszHvVGI",
    "license_url": "https://unsplash.com/license",
    "path": "/salah_timetable/backgrounds/hassan-ii-mosque.webp",
    "position": "center"
  },
  {
    "id": "great-mosque-of-kairouan",
    "name": "Great Mosque of Kairouan",
    "country": "Tunisia",
    "photographer": "Malek Boukhris",
    "source_url": "https://unsplash.com/photos/great-mosque-of-kairouan-in-tunisia-0-Sn6xvf3BM",
    "license_url": "https://unsplash.com/license",
    "path": "/salah_timetable/backgrounds/great-mosque-of-kairouan.webp",
    "position": "center"
  },
  {
    "id": "baiturrahman-grand-mosque",
    "name": "Baiturrahman Grand Mosque",
    "country": "Indonesia",
    "photographer": "Sangga Rima Roman Selia",
    "source_url": "https://unsplash.com/photos/white-concrete-building-during-daytime-2lbcJYnxvqw",
    "license_url": "https://unsplash.com/license",
    "path": "/salah_timetable/backgrounds/baiturrahman-grand-mosque.webp",
    "position": "center"
  }
]);

/** Stable day-based rotation; independent of browser refreshes. */
export function chooseMosqueBackground(items, selection = "daily", day = "") {
  if (!Array.isArray(items) || !items.length || selection === "none") return null;
  if (selection !== "daily") return items.find(item => item.id === selection) || null;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return null;
  const epoch = Date.parse(day + "T00:00:00Z");
  if (!Number.isFinite(epoch)) return null;
  return items[((Math.floor(epoch / 86400000) % items.length) + items.length) % items.length];
}
