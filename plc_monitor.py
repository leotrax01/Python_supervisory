"""Monitor de falhas de PLC Mitsubishi via protocolo MC (3E)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Set

import pymcprotocol


@dataclass(frozen=True)
class PLCConfig:
    ip: str = "192.168.0.10"
    port: int = 5000
    head_device: str = "D1000"
    read_size: int = 3


FALHAS: Dict[int, str] = {
    0: "Falha Motor Principal",
    1: "Falha Inversor",
    2: "Emergência Acionada",
    3: "Sobrecarga",
    4: "Sensor Desalinhado",
    5: "Falha Comunicação CC-Link",
}


class PLCFaultMonitor:
    """Lê palavras do PLC e converte bits para falhas ativas/inativas."""

    def __init__(self, config: PLCConfig | None = None, falhas: Dict[int, str] | None = None) -> None:
        self.config = config or PLCConfig()
        self.falhas = falhas or FALHAS
        self._plc = pymcprotocol.Type3E()
        self._estado_anterior: List[int] = [0] * self.config.read_size

    def connect(self) -> None:
        """Abre conexão com o PLC."""
        self._plc.connect(self.config.ip, self.config.port)

    def disconnect(self) -> None:
        """Fecha conexão com o PLC, se disponível."""
        close_fn = getattr(self._plc, "close", None)
        if callable(close_fn):
            close_fn()

    def read_words(self) -> List[int]:
        """Lê bloco de words configurado no PLC."""
        values = self._plc.batchread_wordunits(
            headdevice=self.config.head_device,
            readsize=self.config.read_size,
        )
        return list(values)

    def active_faults(self, values: List[int]) -> Set[int]:
        """Extrai os bits de falha ativos a partir da leitura de words."""
        ativos: Set[int] = set()

        for word_value in values:
            for bit in self.falhas:
                if (word_value >> bit) & 1:
                    ativos.add(bit)

        return ativos

    def has_state_changed(self, values: List[int]) -> bool:
        changed = values != self._estado_anterior
        if changed:
            self._estado_anterior = list(values)
        return changed

    def build_log_lines(self, active_bits: Set[int]) -> List[str]:
        """Monta as linhas de log para as falhas ativas no instante atual."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        return [f"[{timestamp}] {self.falhas[bit]} ATIVA" for bit in sorted(active_bits)]


__all__ = ["PLCConfig", "PLCFaultMonitor", "FALHAS"]
