"""Plotly summaries built from canonical sales records."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

import plotly.graph_objects as go

from operatix.domain.sales import SaleRecord


def sales_summary(sales: list[SaleRecord]) -> tuple[dict[str, object], go.Figure]:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for sale in sales:
        totals[sale.customer_name] += sale.total_amount

    currencies = sorted({sale.currency for sale in sales})
    metrics: dict[str, object] = {
        "transactions": len(sales),
        "units": sum(sale.quantity for sale in sales),
        "total": float(sum((sale.total_amount for sale in sales), Decimal(0))),
        "currency": currencies[0] if len(currencies) == 1 else "MIXTA",
    }

    figure = go.Figure(
        data=[
            go.Bar(
                x=list(totals.keys()),
                y=[float(value) for value in totals.values()],
                marker_color="#635bff",
            )
        ]
    )
    figure.update_layout(
        title="Ventas acumuladas por cliente",
        xaxis_title="Cliente",
        yaxis_title="Importe",
        template="plotly_white",
        margin={"l": 40, "r": 20, "t": 55, "b": 40},
    )
    return metrics, figure
