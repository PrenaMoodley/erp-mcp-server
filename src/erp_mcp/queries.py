"""Read-only queries behind the MCP tools.

Plain functions that take an Engine and return JSON-friendly dicts, so they are
easy to test without an MCP client. Every query is parameterised and every list
is capped: the caller is a language model, and its input is untrusted.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.engine import Engine

from .db import batches, customers, dispatches, order_lines, products, sales_orders, stock

MAX_ROWS = 50
CENT = Decimal("0.01")
OPEN_STATUSES = ("draft", "approved", "in_production")


class NotFound(LookupError):
    pass


def _jsonable(row: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            v = str(v)
        elif isinstance(v, (date, datetime)):
            v = v.isoformat()
        out[k] = v
    return out


def _rows(engine: Engine, stmt) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        return [_jsonable(dict(r._mapping)) for r in conn.execute(stmt)]


def find_customers(engine: Engine, text: str) -> list[dict]:
    # Escape LIKE wildcards so "%" in the input matches a literal "%".
    escaped = text.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    stmt = (
        select(customers)
        .where(
            or_(
                func.lower(customers.c.name).like(pattern, escape="\\"),
                func.lower(customers.c.code).like(pattern, escape="\\"),
            )
        )
        .order_by(customers.c.name)
        .limit(MAX_ROWS)
    )
    return _rows(engine, stmt)


def get_order(engine: Engine, order_number: str) -> dict:
    header = _rows(
        engine,
        select(sales_orders, customers.c.name.label("customer_name"))
        .join(customers, customers.c.code == sales_orders.c.customer_code)
        .where(sales_orders.c.order_number == order_number),
    )
    if not header:
        raise NotFound(f"No sales order {order_number}")
    lines = _rows(
        engine,
        select(
            order_lines.c.line_no,
            order_lines.c.sku,
            products.c.description,
            order_lines.c.quantity,
            products.c.unit,
            order_lines.c.unit_price,
        )
        .join(products, products.c.sku == order_lines.c.sku)
        .where(order_lines.c.order_number == order_number)
        .order_by(order_lines.c.line_no),
    )
    # Money maths in Decimal, in Python, so results match on SQLite and PostgreSQL.
    total = Decimal("0.00")
    for line in lines:
        line_total = (Decimal(str(line["unit_price"])) * line["quantity"]).quantize(CENT)
        line["unit_price"] = str(Decimal(str(line["unit_price"])).quantize(CENT))
        line["line_total"] = str(line_total)
        total += line_total
    return {**header[0], "lines": lines, "total_excl_vat": str(total)}


def trace_order(engine: Engine, order_number: str) -> dict:
    """The order's path: customer PO -> sales order -> batches -> dispatch -> delivery."""
    order = get_order(engine, order_number)
    events = [
        {"step": "customer_po", "reference": order["customer_po"], "at": order["order_date"]},
        {"step": "sales_order", "reference": order_number, "status": order["status"]},
    ]
    for b in _rows(
        engine,
        select(batches).where(batches.c.order_number == order_number).order_by(batches.c.batch_number),
    ):
        events.append(
            {
                "step": "batch",
                "reference": b["batch_number"],
                "sku": b["sku"],
                "quantity": b["quantity"],
                "at": b["produced_at"],
            }
        )
    for d in _rows(
        engine,
        select(dispatches).where(dispatches.c.order_number == order_number),
    ):
        events.append({"step": "dispatch", "reference": d["dispatch_number"], "at": d["dispatched_at"]})
        if d["delivered_at"]:
            events.append({"step": "delivered", "reference": d["pod_reference"], "at": d["delivered_at"]})

    ordered = {line["sku"]: line["quantity"] for line in order["lines"]}
    produced: dict[str, int] = {}
    for e in events:
        if e["step"] == "batch":
            produced[e["sku"]] = produced.get(e["sku"], 0) + e["quantity"]
    gaps = [
        {"sku": sku, "ordered": qty, "produced": produced.get(sku, 0)}
        for sku, qty in ordered.items()
        if produced.get(sku, 0) < qty
    ]
    return {"order_number": order_number, "events": events, "production_shortfalls": gaps}


def stock_position(engine: Engine, sku: str) -> dict:
    product = _rows(engine, select(products).where(products.c.sku == sku))
    if not product:
        raise NotFound(f"No product {sku}")
    locations = _rows(
        engine,
        select(
            stock.c.location,
            stock.c.on_hand,
            stock.c.reserved,
            (stock.c.on_hand - stock.c.reserved).label("available"),
        )
        .where(stock.c.sku == sku)
        .order_by(stock.c.location),
    )
    open_demand = _rows(
        engine,
        select(func.coalesce(func.sum(order_lines.c.quantity), 0).label("qty"))
        .join(sales_orders, sales_orders.c.order_number == order_lines.c.order_number)
        .where(and_(order_lines.c.sku == sku, sales_orders.c.status.in_(OPEN_STATUSES))),
    )[0]["qty"]
    available = sum(loc["available"] for loc in locations)
    return {
        **product[0],
        "locations": locations,
        "total_available": available,
        "open_order_demand": int(open_demand),
    }


def open_orders(
    engine: Engine, customer_code: str | None = None, due_before: str | None = None
) -> list[dict]:
    stmt = (
        select(
            sales_orders.c.order_number,
            sales_orders.c.customer_code,
            customers.c.name.label("customer_name"),
            sales_orders.c.customer_po,
            sales_orders.c.due_date,
            sales_orders.c.status,
        )
        .join(customers, customers.c.code == sales_orders.c.customer_code)
        .where(sales_orders.c.status.in_(OPEN_STATUSES))
        .order_by(sales_orders.c.due_date)
        .limit(MAX_ROWS)
    )
    if customer_code:
        stmt = stmt.where(sales_orders.c.customer_code == customer_code)
    if due_before:
        stmt = stmt.where(sales_orders.c.due_date < date.fromisoformat(due_before))
    return _rows(engine, stmt)
