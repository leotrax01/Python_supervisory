"""Interface gráfica para monitoramento de falhas do PLC."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from app_controller import MonitoringController
from plc_monitor import PLCFaultMonitor


class SupervisoryApp:
    def __init__(self) -> None:
        self.monitor = PLCFaultMonitor()

        self.root = tk.Tk()
        self.root.title("SCADA 4.0 - Monitor de Falhas")
        self.root.geometry("900x650")
        self.root.configure(bg="black")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.connection_status = tk.StringVar(value="Desconectado")
        self.active_faults_var = tk.StringVar(value="Nenhuma falha ativa.")

        self.controller = MonitoringController(
            monitor=self.monitor,
            on_faults=lambda bits: self.root.after(0, self._render_active_faults, bits),
            on_log=lambda line: self.root.after(0, self._append_log, line),
            on_connection_change=lambda is_ok, msg: self.root.after(0, self._on_connection_change, is_ok, msg),
        )

        self._build_ui()

    def _build_ui(self) -> None:
        tk.Label(
            self.root,
            text="MONITOR DE FALHAS",
            font=("Arial", 20, "bold"),
            fg="white",
            bg="black",
        ).pack(pady=8)

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

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_ativas = tk.Frame(notebook, bg="black")
        self.tab_cadastro = tk.Frame(notebook, bg="#1a1a1a")
        notebook.add(self.tab_ativas, text="Falhas Ativas")
        notebook.add(self.tab_cadastro, text="Falhas Cadastradas")

        self._build_active_tab()
        self._build_registry_tab()

    def _build_active_tab(self) -> None:
        tk.Label(
            self.tab_ativas,
            text="Somente falhas ativas no momento:",
            font=("Arial", 12, "bold"),
            fg="white",
            bg="black",
        ).pack(anchor="w", padx=10, pady=(10, 2))

        tk.Label(
            self.tab_ativas,
            textvariable=self.active_faults_var,
            justify=tk.LEFT,
            font=("Arial", 12),
            fg="red",
            bg="black",
            anchor="w",
        ).pack(fill=tk.X, padx=10)

        self.log_area = scrolledtext.ScrolledText(self.tab_ativas, width=100, height=24)
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _build_registry_tab(self) -> None:
        form = tk.Frame(self.tab_cadastro, bg="#1a1a1a")
        form.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(form, text="Endereço D:", fg="white", bg="#1a1a1a").grid(row=0, column=0, sticky="w")
        self.entry_d = tk.Entry(form, width=12)
        self.entry_d.insert(0, "D1006")
        self.entry_d.grid(row=0, column=1, padx=6)

        tk.Label(form, text="Descrição:", fg="white", bg="#1a1a1a").grid(row=0, column=2, sticky="w")
        self.entry_desc = tk.Entry(form, width=40)
        self.entry_desc.grid(row=0, column=3, padx=6)

        tk.Button(form, text="Cadastrar", command=self._register_fault).grid(row=0, column=4, padx=6)
        tk.Button(form, text="Deletar selecionada", command=self._delete_selected_fault).grid(row=0, column=5, padx=6)

        self.tree = ttk.Treeview(self.tab_cadastro, columns=("addr", "desc"), show="headings", height=20)
        self.tree.heading("addr", text="Endereço")
        self.tree.heading("desc", text="Descrição")
        self.tree.column("addr", width=120, anchor=tk.CENTER)
        self.tree.column("desc", width=620, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._refresh_registered_faults()

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
        self._refresh_registered_faults()
        self._append_log(f"Falha cadastrada/atualizada: D{d_address} - {description}")
        self.entry_d.delete(0, tk.END)
        self.entry_desc.delete(0, tk.END)

    def _delete_selected_fault(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Cadastro", "Selecione uma falha para deletar.")
            return

        item_id = selected[0]
        addr_text = self.tree.item(item_id, "values")[0]
        d_address = self._parse_d_address(str(addr_text))

        self.monitor.delete_fault(d_address)
        self._refresh_registered_faults()
        self._append_log(f"Falha deletada: D{d_address}")

    def _refresh_registered_faults(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for addr, desc in sorted(self.monitor.get_faults().items()):
            self.tree.insert("", tk.END, values=(f"D{addr}", desc))

    def start(self) -> None:
        self.controller.start()
        self.root.mainloop()

    def _on_connection_change(self, is_connected: bool, message: str) -> None:
        self.connection_status.set("Conectado" if is_connected else "Desconectado")
        if is_connected:
            messagebox.showinfo("Conexão", message)
        self._append_log(message)

    def _render_active_faults(self, active_addresses: set[int]) -> None:
        all_faults = self.monitor.get_faults()
        active_lines = [f"D{addr} - {all_faults[addr]}" for addr in sorted(active_addresses) if addr in all_faults]
        self.active_faults_var.set("\n".join(active_lines) if active_lines else "Nenhuma falha ativa.")

        for line in self.monitor.build_log_lines(active_addresses):
            self._append_log(line)

    def _append_log(self, line: str) -> None:
        self.log_area.insert(tk.END, f"{line}\n")
        self.log_area.see(tk.END)

    def on_close(self) -> None:
        self.controller.stop()
        self.monitor.close()
        self.root.destroy()


if __name__ == "__main__":
    SupervisoryApp().start()
