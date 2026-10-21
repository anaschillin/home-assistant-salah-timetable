"""Absolute timestamps for today's published prayer times."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .model import PrayerField

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
        if self.coordinator.data is None:
            return None
        values = self.coordinator.data.timestamps(
            PrayerField(self.entity_description.key), self.coordinator.zone
        )
        return values[0] if values else None

    @property
    def extra_state_attributes(self):
        if self.coordinator.data is None:
            return {}
        values = self.coordinator.data.timestamps(
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
