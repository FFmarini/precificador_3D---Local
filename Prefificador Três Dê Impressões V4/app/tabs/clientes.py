import tkinter as tk
from tkinter import ttk, messagebox
from app.db import db_connect


class ClientesTab(ttk.Frame):
    def __init__(self, master, on_registry_change=None):
        super().__init__(master)
        self.on_registry_change = on_registry_change
        self.edit_id = None
        self._build_ui()

    def _build_ui(self):
        frm = ttk.LabelFrame(self, text="Novo / Editar Cliente")
        frm.pack(fill="x", padx=10, pady=10)

        self.var_name = tk.StringVar()
        self.var_phone = tk.StringVar()
        self.var_instagram = tk.StringVar()
        self.var_city = tk.StringVar()
        self.var_notes = tk.StringVar()

        r = 0
        ttk.Label(frm, text="Nome").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_name, width=40).grid(row=r, column=1, sticky="w", padx=5)
        ttk.Label(frm, text="Telefone").grid(row=r, column=2, sticky="w")
        ttk.Entry(frm, textvariable=self.var_phone, width=20).grid(row=r, column=3, sticky="w", padx=5)
        ttk.Label(frm, text="Instagram").grid(row=r, column=4, sticky="w")
        ttk.Entry(frm, textvariable=self.var_instagram, width=25).grid(row=r, column=5, sticky="w", padx=5)

        r += 1
        ttk.Label(frm, text="Cidade").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_city, width=25).grid(row=r, column=1, sticky="w", padx=5)
        ttk.Label(frm, text="Obs").grid(row=r, column=2, sticky="w")
        ttk.Entry(frm, textvariable=self.var_notes, width=60).grid(row=r, column=3, columnspan=3, sticky="we", padx=5)

        btns = ttk.Frame(frm)
        btns.grid(row=2, column=0, columnspan=6, sticky="w", pady=8)
        ttk.Button(btns, text="Novo", command=self.clear).pack(side="left", padx=4)
        ttk.Button(btns, text="Salvar", command=self.save).pack(side="left", padx=4)
        ttk.Button(btns, text="Excluir", command=self.delete).pack(side="left", padx=4)

        lst = ttk.LabelFrame(self, text="Clientes")
        lst.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tree = ttk.Treeview(lst, columns=("id", "name", "phone", "instagram", "city"), show="headings", height=15)
        for c, t, w in [("id", "id", 60), ("name", "nome", 260), ("phone", "telefone", 130),
                        ("instagram", "instagram", 180), ("city", "cidade", 140)]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.load_selected())

    def reload(self):
        with db_connect() as con:
            rows = con.execute("SELECT id,name,phone,instagram,city FROM clients ORDER BY id DESC").fetchall()
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r["id"], r["name"], r["phone"] or "", r["instagram"] or "", r["city"] or ""))

    def clear(self):
        self.edit_id = None
        for v in [self.var_name, self.var_phone, self.var_instagram, self.var_city, self.var_notes]:
            v.set("")

    def load_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        cid = int(self.tree.item(sel[0])["values"][0])
        self.edit_id = cid
        with db_connect() as con:
            r = con.execute("SELECT * FROM clients WHERE id=?", (cid,)).fetchone()
        self.var_name.set(r["name"] or "")
        self.var_phone.set(r["phone"] or "")
        self.var_instagram.set(r["instagram"] or "")
        self.var_city.set(r["city"] or "")
        self.var_notes.set(r["notes"] or "")

    def save(self):
        name = self.var_name.get().strip()
        if not name:
            messagebox.showwarning("Obrigatório", "Informe o nome.")
            return
        with db_connect() as con:
            if self.edit_id:
                con.execute(
                    "UPDATE clients SET name=?, phone=?, instagram=?, city=?, notes=? WHERE id=?",
                    (
                        name,
                        self.var_phone.get().strip() or None,
                        self.var_instagram.get().strip() or None,
                        self.var_city.get().strip() or None,
                        self.var_notes.get().strip() or None,
                        self.edit_id,
                    ),
                )
            else:
                con.execute(
                    "INSERT INTO clients(name,phone,instagram,city,notes,created_at) VALUES(?,?,?,?,?,datetime('now'))",
                    (
                        name,
                        self.var_phone.get().strip() or None,
                        self.var_instagram.get().strip() or None,
                        self.var_city.get().strip() or None,
                        self.var_notes.get().strip() or None,
                    ),
                )
        self.reload()
        if callable(self.on_registry_change):
            self.on_registry_change()
        messagebox.showinfo("OK", "Cliente salvo.")

    def delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um cliente.")
            return
        cid = int(self.tree.item(sel[0])["values"][0])
        if not messagebox.askyesno("Confirmar", "Excluir cliente selecionado?"):
            return
        try:
            with db_connect() as con:
                con.execute("DELETE FROM clients WHERE id=?", (cid,))
            self.reload()
            if callable(self.on_registry_change):
                self.on_registry_change()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível excluir: {e}")
