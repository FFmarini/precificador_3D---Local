from tkinter import ttk
from app.db import db_connect
from app.ui_helpers import fmt_money


class DashboardTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        self.lbl_today = ttk.Label(top, text="Hoje: ...")
        self.lbl_week = ttk.Label(top, text="7 dias: ...")
        self.lbl_month = ttk.Label(top, text="Mês: ...")
        for w in [self.lbl_today, self.lbl_week, self.lbl_month]:
            w.pack(side="left", padx=10)

        self.tree = ttk.Treeview(self, columns=("period", "orders", "revenue", "profit"), show="headings", height=18)
        for c, t, w in [("period", "período", 160), ("orders", "pedidos", 90), ("revenue", "receita", 140), ("profit", "lucro", 140)]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def reload(self):
        with db_connect() as con:
            today = con.execute("""
                SELECT COUNT(*) n, COALESCE(SUM(final_price),0) rev, COALESCE(SUM(profit),0) prof
                FROM orders
                WHERE date(created_at)=date('now')
            """).fetchone()
            week = con.execute("""
                SELECT COUNT(*) n, COALESCE(SUM(final_price),0) rev, COALESCE(SUM(profit),0) prof
                FROM orders
                WHERE date(created_at) >= date('now','-6 day')
            """).fetchone()
            month = con.execute("""
                SELECT COUNT(*) n, COALESCE(SUM(final_price),0) rev, COALESCE(SUM(profit),0) prof
                FROM orders
                WHERE strftime('%Y-%m', created_at)=strftime('%Y-%m','now')
            """).fetchone()

            self.lbl_today.config(text=f"Hoje: {today['n']} pedidos | {fmt_money(today['rev'])} | lucro {fmt_money(today['prof'])}")
            self.lbl_week.config(text=f"7 dias: {week['n']} pedidos | {fmt_money(week['rev'])} | lucro {fmt_money(week['prof'])}")
            self.lbl_month.config(text=f"Mês: {month['n']} pedidos | {fmt_money(month['rev'])} | lucro {fmt_money(month['prof'])}")

            rows = con.execute("""
                SELECT strftime('%Y-%m', created_at) period,
                       COUNT(*) n,
                       COALESCE(SUM(final_price),0) rev,
                       COALESCE(SUM(profit),0) prof
                FROM orders
                GROUP BY strftime('%Y-%m', created_at)
                ORDER BY period DESC
                LIMIT 24
            """).fetchall()

        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r["period"], r["n"], fmt_money(r["rev"]), fmt_money(r["prof"])))
