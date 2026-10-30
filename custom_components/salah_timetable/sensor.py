"""Absolute timestamps for today's published prayer times."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SHOW_HIJRI_DATE, DOMAIN
from .domain.model import PrayerField
from .domain.presentation import dashboard_attributes

# Sensors use coordinator snapshots; no per-entity I/O needs throttling.
PARALLEL_UPDATES = 0

DESCRIPTIONS = tuple(
    SensorEntityDescription(
        key=field.value,
        translation_key=field.value,
        device_class=SensorDeviceClass.TIMESTAMP,
    )
    for field in PrayerField
)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [
            *(
                SalahSensor(entry.runtime_data, entry, description)
                for description in DESCRIPTIONS
            ),
            SourceStatusSensor(entry.runtime_data, entry),
            CoverageStatusSensor(entry.runtime_data, entry),
            CompletenessStatusSensor(entry.runtime_data, entry),
            *(
                EventSensor(entry.runtime_data, entry, key)
                for key in (
                    "next_salah",
                    "next_jamaat",
                    "previous_jamaat",
                    "next_sehri",
                    "next_iftar",
                )
            ),
            RamadanStatusSensor(entry.runtime_data, entry),
            TaraweehStatusSensor(entry.runtime_data, entry),
            DashboardSensor(entry.runtime_data, entry),
        ]
    )


class SalahSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})

    @property
    def available(self):
        return super().available and self.native_value is not None

    @property
    def native_value(self):
        if self.coordinator.data.effective.row is None:
            return None
        values = self.coordinator.data.effective.row.timestamps(
            PrayerField(self.entity_description.key), self.coordinator.zone
        )
        return values[0] if values else None

    @property
    def extra_state_attributes(self):
        if self.coordinator.data.effective.row is None:
            return {}
        values = self.coordinator.data.effective.row.timestamps(
            PrayerField(self.entity_description.key), self.coordinator.zone
        )
        return {
            "timetable_date": self.coordinator.data.day.isoformat(),
            "scheduled_times": [value.isoformat() for value in values],
        }


class SourceStatusSensor(CoordinatorEntity, SensorEntity):
    """Safe source-check status; never exposes URLs or imported values."""

    _attr_has_entity_name = True
    _attr_translation_key = "source_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_options = [
        "not_configured",
        "configured",
        "up_to_date",
        "rejected_version",
        "differs_from_approved",
        "pending_review",
        "error",
    ]

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_source_status"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})

    @property
    def available(self):
        return True

    @property
    def native_value(self):
        return self.coordinator.source_updates.status["status"]

    @property
    def extra_state_attributes(self):
        return {
            key: value
            for key, value in self.coordinator.source_updates.status.items()
            if key != "status"
        }


class CoverageStatusSensor(CoordinatorEntity, SensorEntity):
    """Approved date coverage; warning delivery is an optional automation."""

    _attr_has_entity_name = True
    _attr_translation_key = "coverage_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_options = [
        "not_configured",
        "missing_today",
        "missing_tomorrow",
        "expiring",
        "covered",
    ]

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_coverage_status"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})

    @property
    def native_value(self):
        return self.coordinator.data.coverage.status

    @property
    def extra_state_attributes(self):
        return self.coordinator.data.coverage.attributes()


class CompletenessStatusSensor(CoordinatorEntity, SensorEntity):
    """Required published fields, independent of date-coverage diagnostics."""

    _attr_has_entity_name = True
    _attr_translation_key = "completeness_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_options = ["not_configured", "missing_today", "partial", "complete"]

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_completeness_status"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})

    @property
    def native_value(self):
        return self.coordinator.data.completeness.status

    @property
    def extra_state_attributes(self):
        return self.coordinator.data.completeness.attributes()


class EventSensor(CoordinatorEntity, SensorEntity):
    """An absolute next/previous event; countdowns belong to the frontend."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator)
        self.key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})
        # The card reads previous Jamaat from the dashboard snapshot, and the
        # bundled automations only need upcoming events. Keep the standalone
        # historical timestamp opt-in without changing existing registry choices.
        self._attr_entity_registry_enabled_default = key != "previous_jamaat"

    @property
    def available(self):
        return super().available and self.native_value is not None

    @property
    def native_value(self):
        event = getattr(self.coordinator.data.events, self.key)
        return event.timestamp if event else None

    @property
    def extra_state_attributes(self):
        event = getattr(self.coordinator.data.events, self.key)
        return {"prayer": event.prayer, "field": event.field.value} if event else {}


class RamadanStatusSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "ramadan_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["active", "inactive"]

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_ramadan_status"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})

    @property
    def native_value(self):
        return (
            "active" if self.coordinator.data.effective.ramadan_active else "inactive"
        )


class TaraweehStatusSensor(RamadanStatusSensor):
    _attr_translation_key = "taraweeh_status"
    _attr_options = ["inactive", "scheduled", "after_isha_jamaat"]

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.unique_id}_taraweeh_status"

    @property
    def native_value(self):
        effective = self.coordinator.data.effective
        if not effective.ramadan_active:
            return "inactive"
        return (
            "scheduled"
            if effective.row and PrayerField.TARAWEEH in effective.row.times
            else "after_isha_jamaat"
        )

    @property
    def extra_state_attributes(self):
        return {"description": self.coordinator.data.effective.taraweeh_text}


class DashboardSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "dashboard"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_dashboard"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})
        self.mosque_name = entry.title
        self.entry = entry

    @property
    def native_value(self):
        return self.coordinator.data.day.isoformat()

    @property
    def extra_state_attributes(self):
        return dashboard_attributes(
            self.coordinator.data,
            self.coordinator.zone,
            self.mosque_name,
            show_hijri_date=self.entry.options.get(
                CONF_SHOW_HIJRI_DATE,
                self.entry.data.get(CONF_SHOW_HIJRI_DATE, True),
            ),
        )
