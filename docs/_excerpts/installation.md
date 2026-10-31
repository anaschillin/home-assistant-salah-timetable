Use Home Assistant OS or Home Assistant Container on Linux; these supply the process limits required for PDF extraction. The tested versions are listed in the [compatibility guide](../testing.md#compatibility-test-environments). For the HACS route, [install and configure HACS](https://www.hacs.xyz/docs/use/) first.

1. In HACS, open **Custom repositories**, add `https://github.com/anaschillin/home-assistant-salah-timetable` and select **Integration**.
2. Download **Salah Timetable** and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → Salah Timetable**.
4. Enter the mosque name, a stable mosque ID and its IANA timezone (for example, `Europe/London`). Use a different ID to add another mosque.

This is a **HACS custom repository**, not a listing in the default HACS catalogue. For manual installation, download the desired [stable release](https://github.com/anaschillin/home-assistant-salah-timetable/releases), extract it, and copy the complete `custom_components/salah_timetable` directory into Home Assistant's configuration directory as `config/custom_components/salah_timetable/`. The `manifest.json` must be directly inside that directory, with its `frontend/`, `translations/` and other bundled files alongside it. Restart Home Assistant, then follow steps 3–4 above.
