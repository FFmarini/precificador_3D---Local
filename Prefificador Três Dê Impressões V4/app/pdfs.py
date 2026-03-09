from __future__ import annotations
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

from app.db import get_setting
from app.ui_helpers import fmt_money, seconds_to_hhmmss


def generate_quote_pdf(output_path: str, *, order: dict, client: dict, project: dict, filament: dict | None):
    logo_path = get_setting("pdf_logo_path")
    c = canvas.Canvas(output_path, pagesize=A4)
    w, h = A4

    y = h - 20 * mm

    # Logo
    if logo_path:
        try:
            img = ImageReader(logo_path)
            c.drawImage(img, 20 * mm, y - 18 * mm, width=40 * mm, height=18 * mm, preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    c.setFont("Helvetica-Bold", 16)
    c.drawString(70 * mm, y - 5 * mm, "Orçamento - Três Dê Impressões")

    y -= 28 * mm
    c.setFont("Helvetica", 11)
    c.drawString(20 * mm, y, f"Pedido: {order.get('order_code','')}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Data: {order.get('created_at','')}")
    y -= 10 * mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, "Cliente")
    y -= 7 * mm
    c.setFont("Helvetica", 11)
    c.drawString(20 * mm, y, f"Nome: {client.get('name','')}")
    y -= 6 * mm
    if client.get("phone"):
        c.drawString(20 * mm, y, f"Telefone: {client.get('phone')}")
        y -= 6 * mm
    if client.get("instagram"):
        c.drawString(20 * mm, y, f"Instagram: {client.get('instagram')}")
        y -= 6 * mm
    if client.get("city"):
        c.drawString(20 * mm, y, f"Cidade: {client.get('city')}")
        y -= 6 * mm
    y -= 4 * mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, "Projeto")
    y -= 7 * mm
    c.setFont("Helvetica", 11)
    c.drawString(20 * mm, y, f"Nome: {project.get('name','')}")
    y -= 6 * mm
    if project.get("url"):
        c.drawString(20 * mm, y, f"URL: {project.get('url')}")
        y -= 6 * mm

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, "Impressão")
    y -= 7 * mm
    c.setFont("Helvetica", 11)
    c.drawString(20 * mm, y, f"Quantidade: {order.get('pieces',1)}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Tempo por peça: {seconds_to_hhmmss(order.get('time_seconds_per_piece',0))}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Filamento por peça: {order.get('filament_g_per_piece',0)} g")
    y -= 6 * mm
    if order.get("chosen_color"):
        c.drawString(20 * mm, y, f"Cor escolhida: {order.get('chosen_color')}")
        y -= 6 * mm
    if filament:
        c.drawString(20 * mm, y, f"Filamento: {filament.get('name','')}")
        y -= 6 * mm

    y -= 6 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, y, f"TOTAL: {fmt_money(order.get('final_price',0))}")
    y -= 10 * mm

    c.setFont("Helvetica", 10)
    obs = (order.get("notes") or "").strip()
    if obs:
        c.drawString(20 * mm, y, "Obs:")
        y -= 5 * mm
        text = c.beginText(20 * mm, y)
        text.setFont("Helvetica", 10)
        for line in obs.splitlines():
            text.textLine(line[:110])
        c.drawText(text)

    c.showPage()
    c.save()
