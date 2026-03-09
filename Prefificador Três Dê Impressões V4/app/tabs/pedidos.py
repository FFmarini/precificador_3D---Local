import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from app.db import db_connect, next_order_no, format_order_code, set_setting
from app.ui_helpers import safe_float, parse_time_to_seconds, seconds_to_hhmmss, fmt_money, _parse_id_from_label, FilterCombo
from app.pricing import compute_pricing_farm
from app.pdfs import generate_quote_pdf

STATUSES = ["Orçado", "Produção", "Pronto", "Entregue", "Cancelado"]
PAYMENTS = ["Pix", "Dinheiro", "Cartão", "Boleto", "Transferência"]


class PedidosTab(ttk.Frame):
    def __init__(self, master, on_registry_change=None):
        super().__init__(master)
        self.on_registry_change = on_registry_change

        self.clients = []
        self.projects = []
        self.filaments = []

        self.editing_order_id = None
        self._last_calc = None

        self._build_ui()
        self.reload_lookups()
        self.refresh_orders()

    def _build_ui(self):
        frm = ttk.LabelFrame(self, text="Novo Pedido / Edição")
        frm.pack(fill="x", padx=10, pady=10)

        self.var_client = tk.StringVar()
        self.var_project = tk.StringVar()
        self.var_filament = tk.StringVar()
        self.var_pieces = tk.StringVar(value="1")
        self.var_time_per_piece = tk.StringVar(value="02:00:00")
        self.var_g_per_piece = tk.StringVar(value="40")
        self.var_color = tk.StringVar()
        self.var_status = tk.StringVar(value="Orçado")
        self.var_payment = tk.StringVar(value="Pix")
        self.var_paid = tk.IntVar(value=0)
        self.var_notes = tk.StringVar()

        # Defaults (padrões Bambu Farm / Etsy)
        self.var_fpkg = tk.StringVar(value="120")
        self.var_ekwh = tk.StringVar(value="1,0")
        self.var_watts = tk.StringVar(value="120")
        self.var_mch = tk.StringVar(value="2,5")
        self.var_labor = tk.StringVar(value="5,0")
        self.var_margin = tk.StringVar(value="30")
        self.var_round = tk.StringVar(value="1")

        self.var_fail = tk.StringVar(value="5")
        self.var_over = tk.StringVar(value="10")
        self.var_pack = tk.StringVar(value="2,5")
        self.var_pfee = tk.StringVar(value="10")
        self.var_payfee = tk.StringVar(value="3,5")
        self.var_ship = tk.StringVar(value="0")
        self.var_disc = tk.StringVar(value="0")

        r0 = ttk.Frame(frm)
        r0.pack(fill="x", padx=8, pady=6)

        ttk.Label(r0, text="Cliente:").pack(side="left")
        self.cb_client = FilterCombo(r0, textvariable=self.var_client, width=40, state="normal")
        self.cb_client.pack(side="left", padx=5)

        ttk.Label(r0, text="Projeto:").pack(side="left", padx=(15, 0))
        self.cb_project = FilterCombo(r0, textvariable=self.var_project, width=45, state="normal")
        self.cb_project.pack(side="left", padx=5)

        r1 = ttk.Frame(frm)
        r1.pack(fill="x", padx=8, pady=6)

        ttk.Label(r1, text="Filamento:").pack(side="left")
        self.cb_filament = FilterCombo(r1, textvariable=self.var_filament, width=45, state="normal")
        self.cb_filament.pack(side="left", padx=5)

        ttk.Label(r1, text="Peças:").pack(side="left", padx=(15, 0))
        ttk.Spinbox(r1, from_=1, to=999, width=5, textvariable=self.var_pieces).pack(side="left", padx=5)

        ttk.Label(r1, text="Tempo por peça:").pack(side="left", padx=(15, 0))
        ttk.Entry(r1, textvariable=self.var_time_per_piece, width=12).pack(side="left", padx=5)

        ttk.Label(r1, text="Filamento (g) por peça:").pack(side="left", padx=(15, 0))
        ttk.Entry(r1, textvariable=self.var_g_per_piece, width=10).pack(side="left", padx=5)

        r2 = ttk.Frame(frm)
        r2.pack(fill="x", padx=8, pady=6)

        ttk.Label(r2, text="Cor escolhida:").pack(side="left")
        ttk.Entry(r2, textvariable=self.var_color, width=18).pack(side="left", padx=5)

        ttk.Label(r2, text="Status:").pack(side="left", padx=(15, 0))
        ttk.Combobox(r2, textvariable=self.var_status, values=STATUSES, width=12, state="readonly").pack(side="left", padx=5)

        ttk.Label(r2, text="Pagamento:").pack(side="left", padx=(15, 0))
        ttk.Combobox(r2, textvariable=self.var_payment, values=PAYMENTS, width=12, state="readonly").pack(side="left", padx=5)

        ttk.Checkbutton(r2, text="Pago", variable=self.var_paid).pack(side="left", padx=(15, 0))

        ttk.Label(r2, text="Obs:").pack(side="left", padx=(15, 0))
        ttk.Entry(r2, textvariable=self.var_notes, width=60).pack(side="left", padx=5, fill="x", expand=True)

        # Custos
        cost = ttk.LabelFrame(self, text="Custos e margem (padrões de cálculo)")
        cost.pack(fill="x", padx=10, pady=(0, 10))
        row = ttk.Frame(cost)
        row.pack(fill="x", padx=8, pady=6)

        def add(lbl, var, w=8):
            ttk.Label(row, text=lbl).pack(side="left")
            ttk.Entry(row, textvariable=var, width=w).pack(side="left", padx=5)

        add("Filamento R$/kg", self.var_fpkg)
        add("Energia R$/kWh", self.var_ekwh)
        add("W médios", self.var_watts)
        add("Máquina R$/h", self.var_mch)
        add("Mão de obra (R$) por pedido", self.var_labor, w=10)
        add("Margem %", self.var_margin)
        add("Arredondar R$", self.var_round)

        farm = ttk.LabelFrame(self, text="Etsy / Farm (taxas, falhas, overhead)")
        farm.pack(fill="x", padx=10, pady=(0, 10))
        row2 = ttk.Frame(farm)
        row2.pack(fill="x", padx=8, pady=6)

        def add2(lbl, var, w=8):
            ttk.Label(row2, text=lbl).pack(side="left")
            ttk.Entry(row2, textvariable=var, width=w).pack(side="left", padx=5)

        add2("Falhas %", self.var_fail)
        add2("Overhead %", self.var_over)
        add2("Embalagem R$", self.var_pack)
        add2("Taxa plataforma %", self.var_pfee)
        add2("Taxa pagamento %", self.var_payfee)
        add2("Frete (R$)", self.var_ship)
        add2("Desconto (R$)", self.var_disc)

        # Resultado
        res = ttk.LabelFrame(self, text="Resultado")
        res.pack(fill="x", padx=10, pady=(0, 10))
        self.lbl_cost = ttk.Label(res, text="Custo total (interno): -")
        self.lbl_prod = ttk.Label(res, text="Produto (sem frete): -")
        self.lbl_final = ttk.Label(res, text="TOTAL final (cliente): -")
        self.lbl_fees = ttk.Label(res, text="Taxas estimadas: -")
        self.lbl_profit = ttk.Label(res, text="Lucro estimado: -")
        rr = ttk.Frame(res)
        rr.pack(fill="x", padx=8, pady=6)
        for w in [self.lbl_cost, self.lbl_prod, self.lbl_final, self.lbl_fees, self.lbl_profit]:
            w.pack(side="left", padx=12)

        # Botões
        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(btns, text="Novo", command=self.new_order).pack(side="left", padx=4)
        ttk.Button(btns, text="Calcular", command=self.calculate).pack(side="left", padx=4)
        ttk.Button(btns, text="Salvar", command=self.save_order).pack(side="left", padx=4)
        ttk.Button(btns, text="Editar", command=self.edit_selected).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancelar edição", command=self.cancel_edit).pack(side="left", padx=4)
        ttk.Button(btns, text="Duplicar", command=self.duplicate_selected).pack(side="left", padx=4)
        ttk.Button(btns, text="Excluir", command=self.delete_selected).pack(side="left", padx=4)
        ttk.Button(btns, text="Gerar PDF (cliente)", command=self.export_pdf_client).pack(side="left", padx=4)
        ttk.Button(btns, text="Definir Logo (PDF)", command=self.set_logo).pack(side="left", padx=4)

        # Lista
        lst = ttk.LabelFrame(self, text="Gerenciar pedidos")
        lst.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        top = ttk.Frame(lst)
        top.pack(fill="x", padx=8, pady=6)
        self.var_filter_status = tk.StringVar(value="Todos")
        ttk.Label(top, text="Filtrar status:").pack(side="left")
        ttk.Combobox(top, textvariable=self.var_filter_status, values=["Todos"] + STATUSES, width=14, state="readonly").pack(side="left", padx=5)
        ttk.Button(top, text="Atualizar lista", command=self.refresh_orders).pack(side="left", padx=6)

        cols = ("id", "pedido", "data", "cliente", "projeto", "filamento", "cor", "status", "pagamento", "pago", "pecas", "tempo_pp", "g_pp", "final")
        self.tree = ttk.Treeview(lst, columns=cols, show="headings", height=16)
        headers = {
            "id": "id",
            "pedido": "pedido",
            "data": "data",
            "cliente": "cliente",
            "projeto": "projeto",
            "filamento": "filamento",
            "cor": "cor",
            "status": "status",
            "pagamento": "pagam",
            "pago": "pago",
            "pecas": "pcs",
            "tempo_pp": "tempo/pc",
            "g_pp": "g/pc",
            "final": "final",
        }
        widths = {
            "id": 50,
            "pedido": 95,
            "data": 140,
            "cliente": 190,
            "projeto": 240,
            "filamento": 260,
            "cor": 90,
            "status": 95,
            "pagamento": 90,
            "pago": 55,
            "pecas": 45,
            "tempo_pp": 85,
            "g_pp": 70,
            "final": 95,
        }
        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())

        self._update_result_labels(None)

    def reload_lookups(self):
        with db_connect() as con:
            self.clients = [dict(r) for r in con.execute("SELECT id,name FROM clients ORDER BY name").fetchall()]
            self.projects = [dict(r) for r in con.execute("SELECT id,name FROM projects ORDER BY name").fetchall()]
            self.filaments = [dict(r) for r in con.execute("SELECT id,name,price_per_kg FROM filaments ORDER BY name").fetchall()]
        self._apply_picklists()

    def _apply_picklists(self):
        self.cb_client.set_all_values([f"{c['name']}  (#{c['id']})" for c in self.clients])
        self.cb_project.set_all_values([f"{p['name']}  (#{p['id']})" for p in self.projects])
        self.cb_filament.set_all_values([f"{f['name']}  (#{f['id']})" for f in self.filaments])

    def new_order(self):
        self.cancel_edit()
        self.var_pieces.set("1")
        self.var_time_per_piece.set("02:00:00")
        self.var_g_per_piece.set("40")
        self.var_color.set("")
        self.var_status.set("Orçado")
        self.var_payment.set("Pix")
        self.var_paid.set(0)
        self.var_notes.set("")
        self._last_calc = None
        self._update_result_labels(None)

    def cancel_edit(self):
        self.editing_order_id = None

    def _gather_inputs(self):
        client_id = _parse_id_from_label(self.var_client.get())
        project_id = _parse_id_from_label(self.var_project.get())
        filament_id = _parse_id_from_label(self.var_filament.get()) if self.var_filament.get().strip() else None

        if not client_id or not project_id:
            raise ValueError("Selecione Cliente e Projeto.")

        pieces = int(self.var_pieces.get() or 1)
        time_sec_per_piece = parse_time_to_seconds(self.var_time_per_piece.get())
        if time_sec_per_piece <= 0:
            raise ValueError("Tempo por peça inválido. Ex: 02:06:00")

        g_per_piece = safe_float(self.var_g_per_piece.get(), 0.0)
        if g_per_piece <= 0:
            raise ValueError("Filamento (g) por peça inválido.")

        return dict(
            client_id=client_id,
            project_id=project_id,
            filament_id=filament_id,
            pieces=pieces,
            time_sec_per_piece=time_sec_per_piece,
            g_per_piece=g_per_piece,
            chosen_color=(self.var_color.get().strip() or None),
            status=self.var_status.get().strip() or "Orçado",
            payment_method=self.var_payment.get().strip() or "Pix",
            is_paid=int(self.var_paid.get() or 0),
            notes=(self.var_notes.get().strip() or None),
            fpkg=safe_float(self.var_fpkg.get(), 0.0),
            ekwh=safe_float(self.var_ekwh.get(), 0.0),
            watts=safe_float(self.var_watts.get(), 0.0),
            mch=safe_float(self.var_mch.get(), 0.0),
            labor=safe_float(self.var_labor.get(), 0.0),
            margin=safe_float(self.var_margin.get(), 0.0),
            rnd=safe_float(self.var_round.get(), 1.0),
            fail=safe_float(self.var_fail.get(), 0.0),
            over=safe_float(self.var_over.get(), 0.0),
            pack=safe_float(self.var_pack.get(), 0.0),
            pfee=safe_float(self.var_pfee.get(), 0.0),
            payfee=safe_float(self.var_payfee.get(), 0.0),
            ship=safe_float(self.var_ship.get(), 0.0),
            disc=safe_float(self.var_disc.get(), 0.0),
        )

    def calculate(self):
        try:
            inp = self._gather_inputs()
            calc = compute_pricing_farm(
                pieces=inp["pieces"],
                time_sec_per_piece=inp["time_sec_per_piece"],
                filament_g_per_piece=inp["g_per_piece"],
                filament_price_per_kg=inp["fpkg"],
                energy_price_per_kwh=inp["ekwh"],
                printer_avg_watts=inp["watts"],
                machine_cost_per_hour=inp["mch"],
                labor_cost_fixed=inp["labor"],
                margin_percent=inp["margin"],
                round_to=inp["rnd"],
                failure_rate_percent=inp["fail"],
                overhead_percent=inp["over"],
                packaging_cost=inp["pack"],
                platform_fee_percent=inp["pfee"],
                payment_fee_percent=inp["payfee"],
                shipping_price=inp["ship"],
                discount_value=inp["disc"],
            )
            self._last_calc = calc
            self._update_result_labels(calc)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha no cálculo: {e}")

    def _update_result_labels(self, calc):
        if not calc:
            self.lbl_cost.config(text="Custo total (interno): -")
            self.lbl_prod.config(text="Produto (sem frete): -")
            self.lbl_final.config(text="TOTAL final (cliente): -")
            self.lbl_fees.config(text="Taxas estimadas: -")
            self.lbl_profit.config(text="Lucro estimado: -")
            return
        self.lbl_cost.config(text=f"Custo total (interno):  {fmt_money(calc['total_cost'])}")
        self.lbl_prod.config(text=f"Produto (sem frete):  {fmt_money(calc['product_price'])}")
        self.lbl_final.config(text=f"TOTAL final (cliente):  {fmt_money(calc['total_final'])}")
        self.lbl_fees.config(text=f"Taxas estimadas:  {fmt_money(calc['fees_estimated'])}")
        self.lbl_profit.config(text=f"Lucro estimado:  {fmt_money(calc['profit'])}")

    def save_order(self):
        try:
            if not self._last_calc:
                self.calculate()
            if not self._last_calc:
                return

            inp = self._gather_inputs()
            calc = self._last_calc

            with db_connect() as con:
                if self.editing_order_id:
                    con.execute(
                        """
                        UPDATE orders SET
                            client_id=?, project_id=?, filament_id=?,
                            pieces=?, time_seconds_per_piece=?, filament_g_per_piece=?,
                            chosen_color=?, status=?, payment_method=?, is_paid=?,
                            notes=?,
                            filament_price_per_kg=?, energy_price_per_kwh=?, printer_avg_watts=?, machine_cost_per_hour=?,
                            labor_cost_fixed=?, margin_percent=?, round_to=?,
                            failure_rate_percent=?, overhead_percent=?, packaging_cost=?, platform_fee_percent=?, payment_fee_percent=?,
                            shipping_price=?, discount_value=?,
                            total_cost=?, product_price=?, fees_estimated=?, profit=?, final_price=?
                        WHERE id=?
                        """,
                        (
                            inp["client_id"],
                            inp["project_id"],
                            inp["filament_id"],
                            inp["pieces"],
                            inp["time_sec_per_piece"],
                            inp["g_per_piece"],
                            inp["chosen_color"],
                            inp["status"],
                            inp["payment_method"],
                            inp["is_paid"],
                            inp["notes"],
                            inp["fpkg"],
                            inp["ekwh"],
                            inp["watts"],
                            inp["mch"],
                            inp["labor"],
                            inp["margin"],
                            inp["rnd"],
                            inp["fail"],
                            inp["over"],
                            inp["pack"],
                            inp["pfee"],
                            inp["payfee"],
                            inp["ship"],
                            inp["disc"],
                            calc["total_cost"],
                            calc["product_price"],
                            calc["fees_estimated"],
                            calc["profit"],
                            calc["total_final"],
                            self.editing_order_id,
                        ),
                    )
                    self.editing_order_id = None
                else:
                    order_no = next_order_no()
                    con.execute(
                        """
                        INSERT INTO orders (
                            order_no, created_at,
                            client_id, project_id, filament_id,
                            pieces, time_seconds_per_piece, filament_g_per_piece,
                            chosen_color, status, payment_method, is_paid, notes,
                            filament_price_per_kg, energy_price_per_kwh, printer_avg_watts, machine_cost_per_hour,
                            labor_cost_fixed, margin_percent, round_to,
                            failure_rate_percent, overhead_percent, packaging_cost, platform_fee_percent, payment_fee_percent,
                            shipping_price, discount_value,
                            total_cost, product_price, fees_estimated, profit, final_price
                        ) VALUES (
                            ?, datetime('now'),
                            ?, ?, ?,
                            ?, ?, ?,
                            ?, ?, ?, ?, ?,
                            ?, ?, ?, ?,
                            ?, ?, ?,
                            ?, ?, ?, ?, ?,
                            ?, ?,
                            ?, ?, ?, ?, ?
                        )
                        """,
                        (
                            order_no,
                            inp["client_id"],
                            inp["project_id"],
                            inp["filament_id"],
                            inp["pieces"],
                            inp["time_sec_per_piece"],
                            inp["g_per_piece"],
                            inp["chosen_color"],
                            inp["status"],
                            inp["payment_method"],
                            inp["is_paid"],
                            inp["notes"],
                            inp["fpkg"],
                            inp["ekwh"],
                            inp["watts"],
                            inp["mch"],
                            inp["labor"],
                            inp["margin"],
                            inp["rnd"],
                            inp["fail"],
                            inp["over"],
                            inp["pack"],
                            inp["pfee"],
                            inp["payfee"],
                            inp["ship"],
                            inp["disc"],
                            calc["total_cost"],
                            calc["product_price"],
                            calc["fees_estimated"],
                            calc["profit"],
                            calc["total_final"],
                        ),
                    )

            self.refresh_orders()
            if callable(self.on_registry_change):
                self.on_registry_change()
            messagebox.showinfo("OK", "Pedido salvo.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar: {e}")

    def refresh_orders(self):
        st = self.var_filter_status.get()
        where = ""
        args = ()
        if st and st != "Todos":
            where = "WHERE o.status=?"
            args = (st,)
        with db_connect() as con:
            rows = con.execute(
                f"""
                SELECT o.*, c.name client_name, p.name project_name, f.name filament_name
                FROM orders o
                JOIN clients c ON c.id=o.client_id
                JOIN projects p ON p.id=o.project_id
                LEFT JOIN filaments f ON f.id=o.filament_id
                {where}
                ORDER BY o.id DESC
                """,
                args,
            ).fetchall()

        self.tree.delete(*self.tree.get_children())
        for r in rows:
            code = format_order_code(r["order_no"])
            self.tree.insert(
                "",
                "end",
                values=(
                    r["id"],
                    code,
                    r["created_at"],
                    r["client_name"],
                    r["project_name"],
                    r["filament_name"] or "",
                    r["chosen_color"] or "",
                    r["status"],
                    r["payment_method"],
                    "Sim" if r["is_paid"] else "Não",
                    r["pieces"],
                    seconds_to_hhmmss(r["time_seconds_per_piece"]),
                    f"{r['filament_g_per_piece']:.2f}",
                    fmt_money(r["final_price"]),
                ),
            )

    def _selected_order_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return int(self.tree.item(sel[0])["values"][0])

    def edit_selected(self):
        oid = self._selected_order_id()
        if not oid:
            messagebox.showwarning("Aviso", "Selecione um pedido.")
            return

        with db_connect() as con:
            o = con.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
            c = con.execute("SELECT id,name FROM clients WHERE id=?", (o["client_id"],)).fetchone()
            p = con.execute("SELECT id,name FROM projects WHERE id=?", (o["project_id"],)).fetchone()
            f = con.execute("SELECT id,name FROM filaments WHERE id=?", (o["filament_id"],)).fetchone() if o["filament_id"] else None

        self.editing_order_id = oid
        self.var_client.set(f"{c['name']}  (#{c['id']})")
        self.var_project.set(f"{p['name']}  (#{p['id']})")
        self.var_filament.set(f"{f['name']}  (#{f['id']})" if f else "")
        self.var_pieces.set(str(o["pieces"]))
        self.var_time_per_piece.set(seconds_to_hhmmss(o["time_seconds_per_piece"]))
        self.var_g_per_piece.set(str(o["filament_g_per_piece"]))
        self.var_color.set(o["chosen_color"] or "")
        self.var_status.set(o["status"] or "Orçado")
        self.var_payment.set(o["payment_method"] or "Pix")
        self.var_paid.set(int(o["is_paid"] or 0))
        self.var_notes.set(o["notes"] or "")

        self.var_fpkg.set(str(o["filament_price_per_kg"] or "0"))
        self.var_ekwh.set(str(o["energy_price_per_kwh"] or "0"))
        self.var_watts.set(str(o["printer_avg_watts"] or "0"))
        self.var_mch.set(str(o["machine_cost_per_hour"] or "0"))
        self.var_labor.set(str(o["labor_cost_fixed"] or "0"))
        self.var_margin.set(str(o["margin_percent"] or "0"))
        self.var_round.set(str(o["round_to"] or "1"))

        self.var_fail.set(str(o["failure_rate_percent"] or "0"))
        self.var_over.set(str(o["overhead_percent"] or "0"))
        self.var_pack.set(str(o["packaging_cost"] or "0"))
        self.var_pfee.set(str(o["platform_fee_percent"] or "0"))
        self.var_payfee.set(str(o["payment_fee_percent"] or "0"))
        self.var_ship.set(str(o["shipping_price"] or "0"))
        self.var_disc.set(str(o["discount_value"] or "0"))

        self._last_calc = {
            "total_cost": o["total_cost"],
            "product_price": o["product_price"],
            "fees_estimated": o["fees_estimated"],
            "profit": o["profit"],
            "total_final": o["final_price"],
        }
        self._update_result_labels(self._last_calc)

    def duplicate_selected(self):
        oid = self._selected_order_id()
        if not oid:
            messagebox.showwarning("Aviso", "Selecione um pedido.")
            return
        self.edit_selected()
        self.editing_order_id = None
        messagebox.showinfo("Duplicado", "Pedido carregado. Ajuste o que quiser e clique em Salvar para criar uma cópia.")

    def delete_selected(self):
        oid = self._selected_order_id()
        if not oid:
            messagebox.showwarning("Aviso", "Selecione um pedido.")
            return
        if not messagebox.askyesno("Confirmar", "Excluir pedido selecionado?"):
            return
        try:
            with db_connect() as con:
                con.execute("DELETE FROM orders WHERE id=?", (oid,))
            self.refresh_orders()
            if callable(self.on_registry_change):
                self.on_registry_change()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível excluir: {e}")

    def set_logo(self):
        path = filedialog.askopenfilename(title="Selecionar logo", filetypes=[("Imagens", "*.png;*.jpg;*.jpeg")])
        if not path:
            return
        set_setting("pdf_logo_path", path)
        messagebox.showinfo("OK", "Logo definido para o PDF.")

    def export_pdf_client(self):
        oid = self._selected_order_id()
        if not oid:
            messagebox.showwarning("Aviso", "Selecione um pedido.")
            return
        with db_connect() as con:
            o = dict(con.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone())
            c = dict(con.execute("SELECT * FROM clients WHERE id=?", (o["client_id"],)).fetchone())
            p = dict(con.execute("SELECT * FROM projects WHERE id=?", (o["project_id"],)).fetchone())
            f = dict(con.execute("SELECT * FROM filaments WHERE id=?", (o["filament_id"],)).fetchone()) if o["filament_id"] else None

        o["order_code"] = format_order_code(o["order_no"])

        out_dir = Path("orcamentos")
        out_dir.mkdir(exist_ok=True)
        pdf_path = out_dir / f"{o['order_code']}.pdf"
        try:
            generate_quote_pdf(str(pdf_path), order=o, client=c, project=p, filament=f)
            messagebox.showinfo("OK", f"PDF gerado em: {pdf_path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao gerar PDF: {e}")
