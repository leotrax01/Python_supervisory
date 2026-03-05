"""Controle de execução (start/pause) e watchdog de conexão com PLC."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from plc_monitor import PLCFaultMonitor


class MonitoringController:
    """Gerencia ciclo de leitura, pausa/retomada e reconexão automática."""

    def __init__(
        self,
        monitor: PLCFaultMonitor,
        on_faults: Callable[[set[str]], None],
        on_log: Callable[[str], None],
        on_connection_change: Callable[[bool, str], None],
        poll_interval: float = 0.5,
        watchdog_timeout: float = 3.0,
    ) -> None:
        self.monitor = monitor
        self.on_faults = on_faults
        self.on_log = on_log
        self.on_connection_change = on_connection_change
        self.poll_interval = poll_interval
        self.watchdog_timeout = watchdog_timeout

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._thread: threading.Thread | None = None

        self._connected = False
        self._last_success_read = 0.0

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.is_running():
            self.resume_monitoring()
            return

        self._stop_event.clear()
        self._pause_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def restart_monitoring(self) -> None:
        self.stop(final_message="Reiniciando monitoramento...")
        self.start()

    def pause_monitoring(self) -> None:
        self._pause_event.set()
        self.on_log("Monitoramento em PAUSE.")

    def resume_monitoring(self) -> None:
        self._pause_event.clear()
        self.on_log("Monitoramento em START.")

    def stop(self, final_message: str = "Aplicação finalizada.") -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None
        self._disconnect(final_message)

    def _run(self) -> None:
        self._connect_if_needed()

        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                time.sleep(0.1)
                continue

            if not self._connected:
                self._connect_if_needed()
                time.sleep(1)
                continue

            try:
                valores = self.monitor.read_fault_values()
                self._last_success_read = time.time()

                if self.monitor.has_state_changed(valores):
                    ativos = self.monitor.active_faults(valores)
                    self.on_faults(ativos)
            except Exception as exc:
                self.on_log(f"Erro de leitura: {exc}")
                self._disconnect("Conexão perdida. Tentando reconectar...")

            if self._connected and (time.time() - self._last_success_read) > self.watchdog_timeout:
                self.on_log("Watchdog: sem resposta do PLC, reconectando...")
                self._disconnect("Watchdog detectou timeout de comunicação.")

            time.sleep(self.poll_interval)

    def _connect_if_needed(self) -> None:
        if self._connected:
            return

        try:
            self.monitor.connect()
            self._connected = True
            self._last_success_read = time.time()
            self.on_connection_change(True, "Conectado ao PLC com sucesso.")
        except Exception as exc:
            self.on_connection_change(False, f"Erro ao conectar no PLC: {exc}")

    def _disconnect(self, message: str) -> None:
        if not self._connected:
            return

        self._connected = False
        self.monitor.disconnect()
        self.on_connection_change(False, message)
