1. In HACS, open **Custom repositories**, add `https://github.com/anaschillin/home-assistant-salah-timetable` and select **Integration**.
2. Download **Salah Timetable** and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → Salah Timetable**.
4. Enter the mosque name, a stable mosque ID and its IANA timezone (for example, `Europe/London`). Use a different ID to add another mosque.

This is a **HACS custom repository**, not a listing in the default HACS catalogue. For manual installation, copy `custom_components/salah_timetable` into Home Assistant's `config/custom_components/` directory and restart.
