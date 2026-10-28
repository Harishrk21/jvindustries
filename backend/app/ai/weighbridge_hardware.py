"""Future TRUWEIGH / weighbridge hardware integration abstraction.

When RS-232 / USB / Ethernet / Bluetooth / API becomes available,
implement a concrete client. Photograph evidence remains mandatory even with direct reads.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class HardwareWeightReading:
    weight_kg: float
    unit: str = "kg"
    source: str = "hardware"
    raw: str | None = None


class WeighbridgeHardwareClient(ABC):
    @abstractmethod
    def read_weight(self) -> Optional[HardwareWeightReading]:
        """Return live weight if hardware connected; otherwise None."""
        raise NotImplementedError


class UnavailableWeighbridgeHardwareClient(WeighbridgeHardwareClient):
    """No hardware configured — application continues with photo + OCR evidence."""

    def read_weight(self) -> Optional[HardwareWeightReading]:
        return None


def get_weighbridge_hardware_client() -> WeighbridgeHardwareClient:
    return UnavailableWeighbridgeHardwareClient()
