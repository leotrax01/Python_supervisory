"""Interface gráfica para monitoramento de falhas do PLC."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext

from app_controller import MonitoringController
from plc_monitor import FALHAS, PLCFaultMonitor


class SupervisoryApp:
    def __init__(self) -> None:
        self.monitor = PLCFaultMonitor()

        self.root = tk.Tk()
        self.root.title("SCADA 4.0 - Monitor de Falhas")
        self.root.geometry("760x560")
        self.root.configure(bg="black")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.labels_falhas: dict[int, tk.Label] = {}
        self.connection_status = tk.StringVar(value="Desconectado")

        self.controller = MonitoringController(
            monitor=self.monitor,
            on_faults=lambda bits: self.root.after(0, self._render_state, bits),
            on_log=lambda line: self.root.after(0, self._append_log, line),
            on_connection_change=lambda is_ok, msg: self.root.after(0, self._on_connection_change, is_ok, msg),
        )

        self._build_ui()

    def _build_ui(self) -> None:
        titulo = tk.Label(
            self.root,
            text="MONITOR DE FALHAS",
            font=("Arial", 20, "bold"),
            fg="white",
            bg="black",
        )
        titulo.pack(pady=10)

        control_frame = tk.Frame(self.root, bg="black")
        control_frame.pack(pady=6)

        btn_start = tk.Button(control_frame, text="START", width=12, command=self.controller.resume_monitoring)
        btn_start.pack(side=tk.LEFT, padx=5)

        btn_pause = tk.Button(control_frame, text="PAUSE", width=12, command=self.controller.pause_monitoring)
        btn_pause.pack(side=tk.LEFT, padx=5)

        status_label = tk.Label(
            control_frame,
            textvariable=self.connection_status,
            font=("Arial", 11, "bold"),
            fg="cyan",
            bg="black",
        )
        status_label.pack(side=tk.LEFT, padx=12)

        frame_falhas = tk.Frame(self.root, bg="black")
        frame_falhas.pack()

        for bit, descricao in FALHAS.items():
            lbl = tk.Label(
                frame_falhas,
                text=descricao,
                font=("Arial", 14),
                fg="green",
                bg="black",
                width=40,
                anchor="w",
            )
            lbl.pack()
            self.labels_falhas[bit] = lbl

        self.log_area = scrolledtext.ScrolledText(self.root, width=86, height=14)
        self.log_area.pack(pady=10)

    def start(self) -> None:
        self.controller.start()
        self.root.mainloop()

    def _on_connection_change(self, is_connected: bool, message: str) -> None:
        self.connection_status.set("Conectado" if is_connected else "Desconectado")

        if is_connected:
            messagebox.showinfo("Conexão", message)

        self._append_log(message)

    def _render_state(self, active_bits: set[int]) -> None:
        for bit, label in self.labels_falhas.items():
            label.config(fg="red" if bit in active_bits else "green")

        for line in self.monitor.build_log_lines(active_bits):
            self._append_log(line)

    def _append_log(self, line: str) -> None:
        self.log_area.insert(tk.END, f"{line}\n")
        self.log_area.see(tk.END)

    def on_close(self) -> None:
        self.controller.stop()
        self.root.destroy()


if __name__ == "__main__":
    SupervisoryApp().start()
