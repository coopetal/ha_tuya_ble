"""The Tuya BLE integration."""
from __future__ import annotations

from dataclasses import dataclass, field

import logging
from typing import Any, Callable

from homeassistant.components.cover import (
    CoverEntityDescription,
    CoverEntity,
    CoverDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .devices import TuyaBLEData, TuyaBLEEntity, TuyaBLEProductInfo
from .tuya_ble import TuyaBLEDataPoint, TuyaBLEDataPointType, TuyaBLEDevice


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
            "bfa138omin59lm6l": [  # Tubular Motor Shade
                TuyaBLECoverMapping(
                    description=CoverEntityDescription(
                        key="tubular_motor_shade",
                        device_class=CoverDeviceClass.SHADE,
                    ),
                    control_dp_id=1,
                    # control_values=["open", "stop", "close", "continue"],
                    percent_control_dp_id=2,
                    percent_state_dp_id=3,
                    control_back_mode_dp_id=5,
                    # control_back_mode_values=["forward", "back"],
                    angle_dp_id=101,
                    reset_dp_id=102,
                    work_state_dp_id=7,
                    # work_state_values=["opening", "closing"],
                    run_mode_dp_id=103,
                    # run_mode_values=["roller", "sheer"],  # Undocumented, need to test values
                    border_dp_id=105,
                    # border_values=["up", "down"],
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

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        if self._mapping.percent_state_dp_id != 0:
            datapoint = self._device.datapoints[self._mapping.percent_state_dp_id]
            if datapoint:
                self._attr_percent_state = datapoint.value

        if self._mapping.percent_control_dp_id != 0:
            datapoint = self._device.datapoints[self._mapping.percent_control_dp_id]
            if datapoint:
                self._attr_percent_control = datapoint.value

        if self._mapping.work_state_dp_id != 0:
            datapoint = self._device.datapoints[self._mapping.work_state_dp_id]
            if datapoint:
                self._attr_work_state = datapoint.value

        if self._mapping.control_back_mode_dp_id != 0:
            datapoint = self._device.datapoints[self._mapping.control_back_mode_dp_id]
            if datapoint:
                self._attr_control_back_mode = datapoint.value

        if self._mapping.angle_dp_id != 0:
            datapoint = self._device.datapoints[self._mapping.angle_dp_id]
            if datapoint:
                self._attr_angle = datapoint.value

        if self._mapping.run_mode_dp_id != 0:
            datapoint = self._device.datapoints[self._mapping.run_mode_dp_id]
            if datapoint:
                self._attr_run_mode = datapoint.value


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
