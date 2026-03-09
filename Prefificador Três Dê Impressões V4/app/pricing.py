from __future__ import annotations
import math


def _round_to(value: float, step: float) -> float:
    step = float(step or 0)
    if step <= 0:
        return float(value)
    return math.ceil(value / step) * step


def compute_pricing_farm(
    *,
    pieces: int,
    time_sec_per_piece: int,
    filament_g_per_piece: float,
    filament_price_per_kg: float,
    energy_price_per_kwh: float,
    printer_avg_watts: float,
    machine_cost_per_hour: float,
    labor_cost_fixed: float,
    margin_percent: float,
    round_to: float,
    failure_rate_percent: float,
    overhead_percent: float,
    packaging_cost: float,
    platform_fee_percent: float,
    payment_fee_percent: float,
    shipping_price: float,
    discount_value: float,
) -> dict:

    pieces = int(pieces or 1)
    time_sec_per_piece = int(time_sec_per_piece or 0)
    filament_g_per_piece = float(filament_g_per_piece or 0)

    total_time_sec = time_sec_per_piece * pieces
    total_g = filament_g_per_piece * pieces

    hours = total_time_sec / 3600.0
    filament_cost = (total_g / 1000.0) * float(filament_price_per_kg or 0)
    energy_cost = hours * (float(printer_avg_watts or 0) / 1000.0) * float(energy_price_per_kwh or 0)
    machine_cost = hours * float(machine_cost_per_hour or 0)

    base_cost = filament_cost + energy_cost + machine_cost + float(labor_cost_fixed or 0)

    # Falhas (refazer %)
    base_cost *= (1.0 + float(failure_rate_percent or 0) / 100.0)

    # Overhead (consumíveis, manutenção, tempo perdido)
    cost_with_overhead = base_cost * (1.0 + float(overhead_percent or 0) / 100.0)

    # Preço produto (sem taxas, sem frete) aplicando margem
    product_price = cost_with_overhead * (1.0 + float(margin_percent or 0) / 100.0)
    product_price = _round_to(product_price, round_to)

    # Taxas estimadas (plataforma + pagamento) sobre o produto
    fees = product_price * (float(platform_fee_percent or 0) / 100.0) + product_price * (float(payment_fee_percent or 0) / 100.0)

    # Final cliente
    final_price = product_price + float(packaging_cost or 0) + float(shipping_price or 0) - float(discount_value or 0)
    final_price = _round_to(final_price, round_to)

    profit = final_price - cost_with_overhead - fees - float(packaging_cost or 0)

    return {
        "pieces": pieces,
        "time_seconds": total_time_sec,
        "filament_g": total_g,
        "total_cost": round(cost_with_overhead, 2),   # custo "interno" já com falhas+overhead
        "product_price": round(product_price, 2),     # produto (sem frete)
        "fees_estimated": round(fees, 2),
        "profit": round(profit, 2),
        "total_final": round(final_price, 2),
        "per_piece_cost": round(cost_with_overhead / max(pieces, 1), 2),
        "per_piece_price": round(product_price / max(pieces, 1), 2),
        "per_piece_profit": round(profit / max(pieces, 1), 2),
    }
