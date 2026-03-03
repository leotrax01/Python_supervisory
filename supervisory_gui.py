"""Interface gráfica para monitoramento de falhas do PLC."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext

from app_controller import MonitoringController
from plc_monitor import PLCFaultMonitor


class SupervisoryApp:
    def __init__(self) -> None:
        self.monitor = PLCFaultMonitor()

        self.root = tk.Tk()
        self.root.title("SCADA 4.0 - Monitor de Falhas")
        self.root.geometry("860x620")
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
        titulo.pack(pady=8)

        control_frame = tk.Frame(self.root, bg="black")
        control_frame.pack(pady=6)

        tk.Button(control_frame, text="START", width=12, command=self.controller.resume_monitoring).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="PAUSE", width=12, command=self.controller.pause_monitoring).pack(side=tk.LEFT, padx=5)

        tk.Label(
            control_frame,
            textvariable=self.connection_status,
            font=("Arial", 11, "bold"),
            fg="cyan",
            bg="black",
        ).pack(side=tk.LEFT, padx=12)

        cadastro = tk.LabelFrame(
            self.root,
            text="Cadastro de falha (Endereço D + Descrição)",
            fg="white",
            bg="black",
            font=("Arial", 10, "bold"),
            padx=8,
            pady=8,
        )
        cadastro.pack(fill=tk.X, padx=10, pady=8)

        tk.Label(cadastro, text="Endereço D:", fg="white", bg="black").grid(row=0, column=0, sticky="w")
        self.entry_d = tk.Entry(cadastro, width=12)
        self.entry_d.insert(0, "D1006")
        self.entry_d.grid(row=0, column=1, padx=6)

        tk.Label(cadastro, text="Descrição:", fg="white", bg="black").grid(row=0, column=2, sticky="w")
        self.entry_desc = tk.Entry(cadastro, width=40)
        self.entry_desc.grid(row=0, column=3, padx=6)

        tk.Button(cadastro, text="Cadastrar Falha", command=self._register_fault).grid(row=0, column=4, padx=6)

        self.frame_falhas = tk.Frame(self.root, bg="black")
        self.frame_falhas.pack(fill=tk.X, padx=10)
        self._rebuild_fault_labels()

        self.log_area = scrolledtext.ScrolledText(self.root, width=100, height=14)
        self.log_area.pack(pady=10)

    def _parse_d_address(self, raw: str) -> int:
        addr = raw.strip().upper().replace(" ", "")
        if addr.startswith("D"):
            addr = addr[1:]
        if not addr.isdigit():
            raise ValueError("Endereço inválido. Use formato D1000 ou 1000.")
        return int(addr)

    def _register_fault(self) -> None:
        try:
            d_address = self._parse_d_address(self.entry_d.get())
        except ValueError as exc:
            messagebox.showerror("Cadastro", str(exc))
            return

        description = self.entry_desc.get().strip()
        if not description:
            messagebox.showerror("Cadastro", "Informe a descrição da falha.")
            return

        self.monitor.add_fault(d_address, description)
        self._rebuild_fault_labels()
        self._append_log(f"Falha cadastrada: D{d_address} - {description}")

        self.entry_d.delete(0, tk.END)
        self.entry_desc.delete(0, tk.END)

    def _rebuild_fault_labels(self) -> None:
        for w in self.frame_falhas.winfo_children():
            w.destroy()

        self.labels_falhas.clear()
        for d_address, descricao in sorted(self.monitor.get_faults().items()):
            lbl = tk.Label(
                self.frame_falhas,
                text=f"D{d_address} - {descricao}",
                font=("Arial", 13),
                fg="green",
                bg="black",
                width=60,
                anchor="w",
            )
            lbl.pack(anchor="w")
            self.labels_falhas[d_address] = lbl

    def start(self) -> None:
        self.controller.start()
        self.root.mainloop()

    def _on_connection_change(self, is_connected: bool, message: str) -> None:
        self.connection_status.set("Conectado" if is_connected else "Desconectado")
        if is_connected:
            messagebox.showinfo("Conexão", message)
        self._append_log(message)

    def _render_state(self, active_addresses: set[int]) -> None:
        for d_address, label in self.labels_falhas.items():
            label.config(fg="red" if d_address in active_addresses else "green")

        for line in self.monitor.build_log_lines(active_addresses):
            self._append_log(line)

    def _append_log(self, line: str) -> None:
        self.log_area.insert(tk.END, f"{line}\n")
        self.log_area.see(tk.END)

    def on_close(self) -> None:
        self.controller.stop()
        self.root.destroy()


if __name__ == "__main__":
    SupervisoryApp().start()
