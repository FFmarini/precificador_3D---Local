import tkinter as tk
from tkinter import ttk, messagebox
from app.db import db_connect
from app.ui_helpers import safe_float


class FilamentosTab(ttk.Frame):
    def __init__(self, master, on_registry_change=None):
        super().__init__(master)
        self.on_registry_change = on_registry_change
        self.edit_id = None
        self._build_ui()

    def _build_ui(self):
        frm = ttk.LabelFrame(self, text="Novo / Editar Filamento")
        frm.pack(fill="x", padx=10, pady=10)

        self.var_name = tk.StringVar()
        self.var_brand = tk.StringVar()
        self.var_type = tk.StringVar()
        self.var_color = tk.StringVar()
        self.var_code = tk.StringVar()
        self.var_price = tk.StringVar(value="0")
        self.var_notes = tk.StringVar()

        r = 0
        ttk.Label(frm, text="Nome").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_name, width=34).grid(row=r, column=1, sticky="w", padx=5)
        ttk.Label(frm, text="Marca").grid(row=r, column=2, sticky="w")
        ttk.Entry(frm, textvariable=self.var_brand, width=20).grid(row=r, column=3, sticky="w", padx=5)
        ttk.Label(frm, text="Tipo").grid(row=r, column=4, sticky="w")
        ttk.Entry(frm, textvariable=self.var_type, width=18).grid(row=r, column=5, sticky="w", padx=5)

        r += 1
        ttk.Label(frm, text="Cor").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_color, width=20).grid(row=r, column=1, sticky="w", padx=5)
        ttk.Label(frm, text="Código").grid(row=r, column=2, sticky="w")
        ttk.Entry(frm, textvariable=self.var_code, width=18).grid(row=r, column=3, sticky="w", padx=5)
        ttk.Label(frm, text="Preço/kg").grid(row=r, column=4, sticky="w")
        ttk.Entry(frm, textvariable=self.var_price, width=10).grid(row=r, column=5, sticky="w", padx=5)

        r += 1
        ttk.Label(frm, text="Obs").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_notes, width=70).grid(row=r, column=1, columnspan=5, sticky="we", padx=5)

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=6, sticky="w", pady=8)
        ttk.Button(btns, text="Novo", command=self.clear).pack(side="left", padx=4)
        ttk.Button(btns, text="Salvar", command=self.save).pack(side="left", padx=4)
        ttk.Button(btns, text="Excluir", command=self.delete).pack(side="left", padx=4)

        lst = ttk.LabelFrame(self, text="Filamentos")
        lst.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tree = ttk.Treeview(lst, columns=("id", "name", "brand", "ftype", "color", "price"), show="headings", height=15)
        cols = [("id", "id", 55), ("name", "nome", 260), ("brand", "marca", 120), ("ftype", "tipo", 120), ("color", "cor", 120), ("price", "R$/kg", 80)]
        for c, t, w in cols:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.load_selected())

    def reload(self):
        with db_connect() as con:
            rows = con.execute("SELECT id,name,brand,ftype,color,price_per_kg FROM filaments ORDER BY id DESC").fetchall()
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r["id"], r["name"], r["brand"] or "", r["ftype"] or "", r["color"] or "", r["price_per_kg"] or 0))

    def clear(self):
        self.edit_id = None
        for v in [self.var_name, self.var_brand, self.var_type, self.var_color, self.var_code, self.var_price, self.var_notes]:
            v.set("")

    def load_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        fid = int(self.tree.item(sel[0])["values"][0])
        self.edit_id = fid
        with db_connect() as con:
            r = con.execute("SELECT * FROM filaments WHERE id=?", (fid,)).fetchone()
        self.var_name.set(r["name"] or "")
        self.var_brand.set(r["brand"] or "")
        self.var_type.set(r["ftype"] or "")
        self.var_color.set(r["color"] or "")
        self.var_code.set(r["code"] or "")
        self.var_price.set(str(r["price_per_kg"] or "0"))
        self.var_notes.set(r["notes"] or "")

    def save(self):
        name = self.var_name.get().strip()
        if not name:
            messagebox.showwarning("Obrigatório", "Informe o nome.")
            return
        price = safe_float(self.var_price.get(), 0.0)
        with db_connect() as con:
            if self.edit_id:
                con.execute(
                    "UPDATE filaments SET name=?,brand=?,ftype=?,color=?,code=?,price_per_kg=?,notes=? WHERE id=?",
                    (
                        name,
                        self.var_brand.get().strip() or None,
                        self.var_type.get().strip() or None,
                        self.var_color.get().strip() or None,
                        self.var_code.get().strip() or None,
                        price,
                        self.var_notes.get().strip() or None,
                        self.edit_id,
                    ),
                )
            else:
                con.execute(
                    "INSERT INTO filaments(name,brand,ftype,color,code,price_per_kg,notes,created_at) VALUES(?,?,?,?,?,?,?,datetime('now'))",
                    (
                        name,
                        self.var_brand.get().strip() or None,
                        self.var_type.get().strip() or None,
                        self.var_color.get().strip() or None,
                        self.var_code.get().strip() or None,
                        price,
                        self.var_notes.get().strip() or None,
                    ),
                )
        self.reload()
        if callable(self.on_registry_change):
            self.on_registry_change()
        messagebox.showinfo("OK", "Filamento salvo.")

    def delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um filamento.")
            return
        fid = int(self.tree.item(sel[0])["values"][0])
        if not messagebox.askyesno("Confirmar", "Excluir filamento selecionado?"):
            return
        try:
            with db_connect() as con:
                con.execute("DELETE FROM filaments WHERE id=?", (fid,))
            self.reload()
            if callable(self.on_registry_change):
                self.on_registry_change()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível excluir: {e}")
