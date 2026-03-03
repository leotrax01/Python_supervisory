"""Interface gráfica para monitoramento de falhas do PLC."""

from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext

from plc_monitor import FALHAS, PLCFaultMonitor


class SupervisoryApp:
    def __init__(self) -> None:
        self.monitor = PLCFaultMonitor()

        self.root = tk.Tk()
        self.root.title("SCADA 4.0 - Monitor de Falhas")
        self.root.geometry("700x500")
        self.root.configure(bg="black")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._running = False
        self.labels_falhas: dict[int, tk.Label] = {}

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

        self.log_area = scrolledtext.ScrolledText(self.root, width=80, height=10)
        self.log_area.pack(pady=10)

    def start(self) -> None:
        try:
            self.monitor.connect()
        except Exception as exc:
            messagebox.showerror("Conexão", f"Erro ao conectar no PLC: {exc}")
            return

        messagebox.showinfo("Conexão", "Conectado ao PLC com sucesso.")

        self._running = True
        thread = threading.Thread(target=self._monitorar_loop, daemon=True)
        thread.start()
        self.root.mainloop()

    def _monitorar_loop(self) -> None:
        while self._running:
            try:
                valores = self.monitor.read_words()
                if self.monitor.has_state_changed(valores):
                    ativos = self.monitor.active_faults(valores)
                    self.root.after(0, self._render_state, ativos)
            except Exception as exc:
                self.root.after(0, self._append_log, f"Erro de leitura: {exc}")

            time.sleep(0.5)

    def _render_state(self, active_bits: set[int]) -> None:
        for bit, label in self.labels_falhas.items():
            label.config(fg="red" if bit in active_bits else "green")

        for line in self.monitor.build_log_lines(active_bits):
            self._append_log(line)

    def _append_log(self, line: str) -> None:
        self.log_area.insert(tk.END, f"{line}\n")
        self.log_area.see(tk.END)

    def on_close(self) -> None:
        self._running = False
        self.monitor.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    SupervisoryApp().start()
