"""Monitor de falhas de PLC Mitsubishi via protocolo MC (3E)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Set

import pymcprotocol

from fault_db import FaultRepository


@dataclass(frozen=True)
class PLCConfig:
    ip: str = "192.168.0.10"
    port: int = 5000


FALHAS_PADRAO: Dict[str, tuple[int, int | None, str]] = {
    "D1000": (1000, None, "Falha Motor Principal"),
    "D1001": (1001, None, "Falha Inversor"),
    "D1002": (1002, None, "Emergência Acionada"),
    "D1003": (1003, None, "Sobrecarga"),
}


class PLCFaultMonitor:
    """Lê points D (word/bit) do PLC e informa quais falhas estão ativas."""

    def __init__(self, config: PLCConfig | None = None, repository: FaultRepository | None = None) -> None:
        self.config = config or PLCConfig()
        self._plc = pymcprotocol.Type3E()
        self.repository = repository or FaultRepository()
        self.repository.seed_defaults(FALHAS_PADRAO)
        self._estado_anterior: Dict[str, int] = {}

    def set_connection_params(self, ip: str, port: int) -> None:
        self.config = PLCConfig(ip=ip, port=port)

    def connect(self) -> None:
        self._plc.connect(self.config.ip, self.config.port)

    def disconnect(self) -> None:
        close_fn = getattr(self._plc, "close", None)
        if callable(close_fn):
            close_fn()

    def close(self) -> None:
        self.repository.close()

    def _parse_point_key(self, point_key: str) -> tuple[str, int, int | None]:
        key = point_key.strip().upper().replace(" ", "")
        if not key.startswith("D"):
            raise ValueError("Ponto inválido. Use D6000 ou D6000.0 até D6000.F")

        body = key[1:]
        if "." not in body:
            if not body.isdigit():
                raise ValueError("Word inválida. Use D6000")
            return (f"D{int(body)}", int(body), None)

        word_part, bit_part = body.split(".", 1)
        if not word_part.isdigit() or bit_part == "":
            raise ValueError("Formato inválido. Use D6000.0 até D6000.F")

        if bit_part.isdigit():
            bit_index = int(bit_part)
        else:
            try:
                bit_index = int(bit_part, 16)
            except ValueError as exc:
                raise ValueError("Bit inválido. Use 0..15 ou 0..F") from exc

        if bit_index < 0 or bit_index > 15:
            raise ValueError("Bit fora do range. Use 0..15")

        word = int(word_part)
        bit_hex = format(bit_index, "X")
        return (f"D{word}.{bit_hex}", word, bit_index)

    def add_fault(self, point_key: str, description: str) -> None:
        canonical_key, word, bit = self._parse_point_key(point_key)
        self.repository.upsert_fault(canonical_key, word, bit, description)
        self._estado_anterior.pop(canonical_key, None)

    def delete_fault(self, point_key: str) -> None:
        canonical_key, _, _ = self._parse_point_key(point_key)
        self.repository.delete_fault(canonical_key)
        self._estado_anterior.pop(canonical_key, None)

    def get_faults(self) -> Dict[str, str]:
        return self.repository.faults_map()

    def read_fault_values(self) -> Dict[str, int]:
        points = self.repository.list_points()
        if not points:
            return {}

        word_addresses = [word for _, word, _, _ in points]
        min_addr = min(word_addresses)
        max_addr = max(word_addresses)
        read_size = (max_addr - min_addr) + 1

        values = self._plc.batchread_wordunits(
            headdevice=f"D{min_addr}",
            readsize=read_size,
        )

        point_values: Dict[str, int] = {}
        for point_key, word, bit, _ in points:
            word_value = int(values[word - min_addr])
            if bit is None:
                point_values[point_key] = word_value
            else:
                point_values[point_key] = (word_value >> bit) & 1

        return point_values

    def has_state_changed(self, values_by_point: Dict[str, int]) -> bool:
        changed = values_by_point != self._estado_anterior
        if changed:
            self._estado_anterior = dict(values_by_point)
        return changed

    def active_faults(self, values_by_point: Dict[str, int]) -> Set[str]:
        return {point_key for point_key, value in values_by_point.items() if value != 0}

    def build_log_lines(self, active_points: Set[str]) -> List[str]:
        timestamp = datetime.now().strftime("%H:%M:%S")
        faults = self.get_faults()
        return [f"[{timestamp}] {point} - {faults[point]} ATIVA" for point in sorted(active_points) if point in faults]


__all__ = ["PLCConfig", "PLCFaultMonitor", "FALHAS_PADRAO"]
