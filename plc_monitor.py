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


FALHAS_PADRAO: Dict[int, str] = {
    1000: "Falha Motor Principal",
    1001: "Falha Inversor",
    1002: "Emergência Acionada",
    1003: "Sobrecarga",
    1004: "Sensor Desalinhado",
    1005: "Falha Comunicação CC-Link",
}


class PLCFaultMonitor:
    """Lê endereços D do PLC e informa quais falhas estão ativas."""

    def __init__(self, config: PLCConfig | None = None, repository: FaultRepository | None = None) -> None:
        self.config = config or PLCConfig()
        self._plc = pymcprotocol.Type3E()
        self.repository = repository or FaultRepository()
        self.repository.seed_defaults(FALHAS_PADRAO)
        self._estado_anterior: Dict[int, int] = {}


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

    def add_fault(self, d_address: int, description: str) -> None:
        self.repository.upsert_fault(d_address, description)
        self._estado_anterior.pop(d_address, None)

    def delete_fault(self, d_address: int) -> None:
        self.repository.delete_fault(d_address)
        self._estado_anterior.pop(d_address, None)

    def get_faults(self) -> Dict[int, str]:
        return self.repository.faults_map()

    def read_fault_values(self) -> Dict[int, int]:
        faults = self.get_faults()
        if not faults:
            return {}

        min_addr = min(faults)
        max_addr = max(faults)
        read_size = (max_addr - min_addr) + 1

        valores = self._plc.batchread_wordunits(
            headdevice=f"D{min_addr}",
            readsize=read_size,
        )

        return {addr: int(valores[addr - min_addr]) for addr in faults}

    def has_state_changed(self, values_by_addr: Dict[int, int]) -> bool:
        changed = values_by_addr != self._estado_anterior
        if changed:
            self._estado_anterior = dict(values_by_addr)
        return changed

    def active_faults(self, values_by_addr: Dict[int, int]) -> Set[int]:
        return {addr for addr, value in values_by_addr.items() if value != 0}

    def build_log_lines(self, active_addresses: Set[int]) -> List[str]:
        timestamp = datetime.now().strftime("%H:%M:%S")
        faults = self.get_faults()
        return [f"[{timestamp}] D{addr} - {faults[addr]} ATIVA" for addr in sorted(active_addresses) if addr in faults]


__all__ = ["PLCConfig", "PLCFaultMonitor", "FALHAS_PADRAO"]
