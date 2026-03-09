import tkinter as tk
from tkinter import ttk, messagebox
from app.db import db_connect


class ProjetosTab(ttk.Frame):
    def __init__(self, master, on_registry_change=None):
        super().__init__(master)
        self.on_registry_change = on_registry_change
        self.edit_id = None
        self._build_ui()

    def _build_ui(self):
        frm = ttk.LabelFrame(self, text="Novo / Editar Projeto")
        frm.pack(fill="x", padx=10, pady=10)

        self.var_name = tk.StringVar()
        self.var_url = tk.StringVar()
        self.var_notes = tk.StringVar()

        ttk.Label(frm, text="Nome").grid(row=0, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_name, width=40).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(frm, text="URL").grid(row=0, column=2, sticky="w")
        ttk.Entry(frm, textvariable=self.var_url, width=45).grid(row=0, column=3, sticky="w", padx=5)

        ttk.Label(frm, text="Obs").grid(row=1, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_notes, width=95).grid(row=1, column=1, columnspan=3, sticky="we", padx=5)

        btns = ttk.Frame(frm)
        btns.grid(row=2, column=0, columnspan=4, sticky="w", pady=8)
        ttk.Button(btns, text="Novo", command=self.clear).pack(side="left", padx=4)
        ttk.Button(btns, text="Salvar", command=self.save).pack(side="left", padx=4)
        ttk.Button(btns, text="Excluir", command=self.delete).pack(side="left", padx=4)

        lst = ttk.LabelFrame(self, text="Projetos")
        lst.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.tree = ttk.Treeview(lst, columns=("id", "name", "url"), show="headings", height=15)
        for c, t, w in [("id", "id", 55), ("name", "nome", 320), ("url", "url", 500)]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.load_selected())

    def reload(self):
        with db_connect() as con:
            rows = con.execute("SELECT id,name,url FROM projects ORDER BY id DESC").fetchall()
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r["id"], r["name"], r["url"] or ""))

    def clear(self):
        self.edit_id = None
        self.var_name.set("")
        self.var_url.set("")
        self.var_notes.set("")

    def load_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        pid = int(self.tree.item(sel[0])["values"][0])
        self.edit_id = pid
        with db_connect() as con:
            r = con.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
        self.var_name.set(r["name"] or "")
        self.var_url.set(r["url"] or "")
        self.var_notes.set(r["notes"] or "")

    def save(self):
        name = self.var_name.get().strip()
        if not name:
            messagebox.showwarning("Obrigatório", "Informe o nome.")
            return
        with db_connect() as con:
            if self.edit_id:
                con.execute("UPDATE projects SET name=?, url=?, notes=? WHERE id=?",
                            (name, self.var_url.get().strip() or None, self.var_notes.get().strip() or None, self.edit_id))
            else:
                con.execute("INSERT INTO projects(name,url,notes,created_at) VALUES(?,?,?,datetime('now'))",
                            (name, self.var_url.get().strip() or None, self.var_notes.get().strip() or None))
        self.reload()
        if callable(self.on_registry_change):
            self.on_registry_change()
        messagebox.showinfo("OK", "Projeto salvo.")

    def delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um projeto.")
            return
        pid = int(self.tree.item(sel[0])["values"][0])
        if not messagebox.askyesno("Confirmar", "Excluir projeto selecionado?"):
            return
        try:
            with db_connect() as con:
                con.execute("DELETE FROM projects WHERE id=?", (pid,))
            self.reload()
            if callable(self.on_registry_change):
                self.on_registry_change()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível excluir: {e}")
