"""The Tuya BLE integration."""
from __future__ import annotations

from dataclasses import dataclass, field

import logging
from typing import Any, Callable

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityDescription,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPoint, TuyaBLEDataPointType, TuyaBLEDevice

_LOGGER = logging.getLogger(__name__)


@dataclass
class TuyaBLECoverMapping:
    description: CoverEntityDescription

    control_dp_id: int = 0
    control_values: list[str] | None = None

    percent_control_dp_id: int = 0

    percent_state_dp_id: int = 0

    control_back_mode_dp_id: int = 0
    control_back_mode_values: list[str] | None = None

    angle_dp_id: int = 0

    reset_dp_id: int = 0

    work_state_dp_id: int = 0
    work_state_values: list[str] | None = None

    run_mode_dp_id: int = 0
    run_mode_values: list[str] | None = None

    border_dp_id: int = 0
    border_values: list[str] | None = None

    fault_dp_id: int = 0


@dataclass
class TuyaBLECategoryCoverMapping:
    products: dict[str, list[TuyaBLECoverMapping]] | None = None
    mapping: list[TuyaBLECoverMapping] | None = None


mapping: dict[str, TuyaBLECategoryCoverMapping] = {
    "cl": TuyaBLECategoryCoverMapping(
        products={
            "y0dtvgqf": [  # Tubular Motor Shade
                TuyaBLECoverMapping(
                    description=CoverEntityDescription(
                        key="tubular_motor_shade",
                        device_class=CoverDeviceClass.SHADE,
                    ),
                    control_dp_id=1,
                    control_values=["open", "stop", "close", "continue"],
                    percent_control_dp_id=2,
                    percent_state_dp_id=3,
                    angle_dp_id=101,
                    reset_dp_id=102,
                    work_state_dp_id=7,
                    border_dp_id=105,
                    fault_dp_id=12,
                ),
            ],
        },
    ),
}


def get_mapping_by_device(device: TuyaBLEDevice) -> list[TuyaBLECoverMapping]:
    category = mapping.get(device.category)
    if category is not None and category.products is not None:
        product_mapping = category.products.get(device.product_id)
        if product_mapping is not None:
            return product_mapping
        if category.mapping is not None:
            return category.mapping
        else:
            return []
    else:
        return []


class TuyaBLECover(TuyaBLEEntity, CoverEntity):
    """Representation of a Tuya BLE Cover."""

    def __init__(
            self,
            hass: HomeAssistant,
            coordinator: DataUpdateCoordinator,
            device: TuyaBLEDevice,
            product: TuyaBLEProductInfo,
            mapping: TuyaBLECoverMapping,
    ) -> None:
        super().__init__(hass, coordinator, device, product, mapping.description)
        self._mapping = mapping

        self._attr_control_values = mapping.control_values

        self._attr_is_closed = True
        self._attr_is_closing = False
        self._attr_is_opening = False

        self._attr_supported_features = CoverEntityFeature.OPEN
        self._attr_supported_features |= CoverEntityFeature.CLOSE
        self._attr_supported_features |= CoverEntityFeature.STOP

        if mapping.percent_control_dp_id and mapping.percent_state_dp_id:
            self._attr_supported_features |= CoverEntityFeature.SET_POSITION
            datapoint = self._device.datapoints[self._mapping.percent_state_dp_id]
            if datapoint:
                inverted_value = 100 - datapoint.value
                self._attr_current_cover_position = inverted_value
                self._attr_is_closed = True if inverted_value == 0 else False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        if self._mapping.percent_state_dp_id != 0:
            datapoint = self._device.datapoints[self._mapping.percent_state_dp_id]
            if datapoint:
                inverted_value = 100 - datapoint.value
                self._attr_current_cover_position = inverted_value
                self._attr_is_closed = True if inverted_value == 0 else False

        self.get_operation_state()

        self.async_write_ha_state()

    def get_operation_state(self) -> None:
        if self._mapping.work_state_dp_id != 0:
            datapoint = self._device.datapoints[self._mapping.work_state_dp_id]
            if datapoint:
                if datapoint.value == "closing":
                    self._attr_is_closing = True
                    self._attr_is_opening = False
                elif datapoint.value == "opening":
                    self._attr_is_closing = False
                    self._attr_is_opening = True
                else:
                    self._attr_is_closing = False
                    self._attr_is_opening = False
            else:
                self._attr_is_closing = False
                self._attr_is_opening = False

    async def async_open_cover(self) -> None:
        int_value = self._attr_control_values.index("open")
        datapoint = self._device.datapoints.get_or_create(
            self._mapping.control_dp_id,
            TuyaBLEDataPointType.DT_ENUM,
            int_value,
        )
        if datapoint:
            self._hass.create_task(datapoint.set_value(int_value))

    async def async_close_cover(self) -> None:
        int_value = self._attr_control_values.index("close")
        datapoint = self._device.datapoints.get_or_create(
            self._mapping.control_dp_id,
            TuyaBLEDataPointType.DT_ENUM,
            int_value,
        )
        if datapoint:
            self._hass.create_task(datapoint.set_value(int_value))

    async def async_stop_cover(self) -> None:
        int_value = self._attr_control_values.index("stop")
        datapoint = self._device.datapoints.get_or_create(
            self._mapping.control_dp_id,
            TuyaBLEDataPointType.DT_ENUM,
            int_value,
        )
        if datapoint:
            self._hass.create_task(datapoint.set_value(int_value))

    async def async_set_cover_position(self, position: int) -> None:
        if self._mapping.percent_control_dp_id != 0:
            int_value = 100 - position
            datapoint = self._device.datapoints.get_or_create(
                self._mapping.percent_control_dp_id,
                TuyaBLEDataPointType.DT_VALUE,
                int_value,
            )
            if datapoint:
                self._hass.create_task(datapoint.set_value(int_value))


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tuya BLE sensors."""
    data: TuyaBLEData = hass.data[DOMAIN][entry.entry_id]
    mappings = get_mapping_by_device(data.device)
    entities: list[TuyaBLECover] = []
    for mapping in mappings:
        entities.append(
            TuyaBLECover(
                hass,
                data.coordinator,
                data.device,
                data.product,
                mapping,
            )
        )
    async_add_entities(entities)
