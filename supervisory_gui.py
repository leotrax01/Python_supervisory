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
        self.root.geometry("920x680")
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

        status_frame = tk.Frame(self.root, bg="black")
        status_frame.pack(pady=4)
        tk.Label(
            status_frame,
            text="Status conexão:",
            font=("Arial", 11, "bold"),
            fg="white",
            bg="black",
        ).pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(
            status_frame,
            textvariable=self.connection_status,
            font=("Arial", 11, "bold"),
            fg="cyan",
            bg="black",
        ).pack(side=tk.LEFT)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_conexao = tk.Frame(notebook, bg="#1a1a1a")
        self.tab_ativas = tk.Frame(notebook, bg="black")
        self.tab_cadastro = tk.Frame(notebook, bg="#1a1a1a")
        notebook.add(self.tab_conexao, text="Conexão PLC")
        notebook.add(self.tab_ativas, text="Falhas Ativas")
        notebook.add(self.tab_cadastro, text="Falhas Cadastradas")

        self._build_connection_tab()
        self._build_active_tab()
        self._build_registry_tab()

    def _build_connection_tab(self) -> None:
        form = tk.Frame(self.tab_conexao, bg="#1a1a1a")
        form.pack(fill=tk.X, padx=10, pady=12)

        tk.Label(form, text="IP do PLC:", fg="white", bg="#1a1a1a").grid(row=0, column=0, sticky="w")
        self.entry_ip = tk.Entry(form, width=20)
        self.entry_ip.insert(0, self.monitor.config.ip)
        self.entry_ip.grid(row=0, column=1, padx=6)

        tk.Label(form, text="Porta:", fg="white", bg="#1a1a1a").grid(row=0, column=2, sticky="w")
        self.entry_port = tk.Entry(form, width=8)
        self.entry_port.insert(0, str(self.monitor.config.port))
        self.entry_port.grid(row=0, column=3, padx=6)

        tk.Button(form, text="Conectar / Iniciar", command=self._start_connection).grid(row=0, column=4, padx=8)
        tk.Button(form, text="Pausar", command=self.controller.pause_monitoring).grid(row=0, column=5, padx=8)

        hint = (
            "Ao clicar em Conectar/Iniciar, o sistema tenta conexão com o PLC e\n"
            "mantém tentativas automáticas de reconexão em caso de falha."
        )
        tk.Label(self.tab_conexao, text=hint, fg="#cfcfcf", bg="#1a1a1a", justify=tk.LEFT).pack(anchor="w", padx=10)

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

        tk.Label(form, text="Ponto PLC:", fg="white", bg="#1a1a1a").grid(row=0, column=0, sticky="w")
        self.entry_d = tk.Entry(form, width=14)
        self.entry_d.insert(0, "D6000.0")
        self.entry_d.grid(row=0, column=1, padx=6)

        tk.Label(form, text="Descrição:", fg="white", bg="#1a1a1a").grid(row=0, column=2, sticky="w")
        self.entry_desc = tk.Entry(form, width=40)
        self.entry_desc.grid(row=0, column=3, padx=6)

        tk.Button(form, text="Cadastrar", command=self._register_fault).grid(row=0, column=4, padx=6)
        tk.Button(form, text="Deletar selecionada", command=self._delete_selected_fault).grid(row=0, column=5, padx=6)

        self.tree = ttk.Treeview(self.tab_cadastro, columns=("addr", "desc"), show="headings", height=20)
        self.tree.heading("addr", text="Ponto")
        self.tree.heading("desc", text="Descrição")
        self.tree.column("addr", width=120, anchor=tk.CENTER)
        self.tree.column("desc", width=640, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._refresh_registered_faults()

    def _start_connection(self) -> None:
        ip = self.entry_ip.get().strip()
        port_text = self.entry_port.get().strip()

        if not ip:
            messagebox.showerror("Conexão", "Informe o IP do PLC.")
            return

        if not port_text.isdigit():
            messagebox.showerror("Conexão", "Porta inválida.")
            return

        port = int(port_text)
        self.monitor.set_connection_params(ip=ip, port=port)

        if self.controller.is_running():
            self.controller.restart_monitoring()
        else:
            self.controller.start()

    def _register_fault(self) -> None:
        point_key = self.entry_d.get().strip()

        description = self.entry_desc.get().strip()
        if not description:
            messagebox.showerror("Cadastro", "Informe a descrição da falha.")
            return

        try:
            self.monitor.add_fault(point_key, description)
        except ValueError as exc:
            messagebox.showerror("Cadastro", str(exc))
            return

        self._refresh_registered_faults()
        self._append_log(f"Falha cadastrada/atualizada: {point_key.upper()} - {description}")
        self.entry_d.delete(0, tk.END)
        self.entry_desc.delete(0, tk.END)

    def _delete_selected_fault(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Cadastro", "Selecione uma falha para deletar.")
            return

        item_id = selected[0]
        point_text = str(self.tree.item(item_id, "values")[0])

        try:
            self.monitor.delete_fault(point_text)
        except ValueError as exc:
            messagebox.showerror("Cadastro", str(exc))
            return

        self._refresh_registered_faults()
        self._append_log(f"Falha deletada: {point_text}")

    def _refresh_registered_faults(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for point, desc in sorted(self.monitor.get_faults().items()):
            self.tree.insert("", tk.END, values=(point, desc))

    def start(self) -> None:
        self.root.mainloop()

    def _on_connection_change(self, is_connected: bool, message: str) -> None:
        self.connection_status.set("Conectado" if is_connected else "Desconectado")
        if is_connected:
            messagebox.showinfo("Conexão", message)
        self._append_log(message)

    def _render_active_faults(self, active_points: set[str]) -> None:
        all_faults = self.monitor.get_faults()
        active_lines = [f"{point} - {all_faults[point]}" for point in sorted(active_points) if point in all_faults]
        self.active_faults_var.set("\n".join(active_lines) if active_lines else "Nenhuma falha ativa.")

        for line in self.monitor.build_log_lines(active_points):
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
