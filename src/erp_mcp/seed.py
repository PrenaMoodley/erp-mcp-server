"""Create the tables and load fictional demo data.

python -m erp_mcp.seed                       # SQLite file erp_demo.db
DATABASE_URL=postgresql+psycopg://... python -m erp_mcp.seed
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Table
from sqlalchemy.engine import Engine

from .db import (
    batches,
    customers,
    dispatches,
    get_engine,
    metadata,
    order_lines,
    products,
    sales_orders,
    stock,
)

CUSTOMERS = [
    ("C1001", "Coastal Bakeries (Pty) Ltd", "Durban"),
    ("C1002", "Berea Fresh Markets CC", "Durban"),
    ("C1003", "Ridgeview Catering Services", "Umhlanga"),
    ("C1004", "Umdloti Juice Co", "North Coast"),
]

PRODUCTS = [
    ("BOX-CAKE-10", "Cake box white 10 inch with window", "each"),
    ("BOX-CAKE-12", "Cake box white 12 inch with window", "each"),
    ("BAG-KRF-M", "Kraft paper bag medium flat handle", "each"),
    ("CUP-PET-500", "PET smoothie cup 500ml clear", "sleeve of 50"),
    ("LID-DOME-95", "Dome lid 95mm with hole", "sleeve of 50"),
    ("CNT-HNG-1L", "Hinged takeaway container 1 litre", "case of 250"),
]

ORDERS = [
    ("SO-24001", "C1001", "CB-2026-0390", date(2026, 9, 21), date(2026, 10, 2), "delivered"),
    ("SO-24002", "C1001", "CB-2026-0418", date(2026, 10, 5), date(2026, 10, 19), "in_production"),
    ("SO-24003", "C1002", "7731", date(2026, 10, 9), date(2026, 10, 16), "approved"),
    ("SO-24004", "C1003", "RCS/PO/0092", date(2026, 10, 2), date(2026, 10, 14), "draft"),
    ("SO-24005", "C1004", "UJC-118", date(2026, 10, 1), date(2026, 10, 8), "dispatched"),
]

LINES = [
    ("SO-24001", 1, "BOX-CAKE-10", 400, "6.80"),
    ("SO-24002", 1, "BOX-CAKE-10", 500, "6.80"),
    ("SO-24002", 2, "BOX-CAKE-12", 250, "8.20"),
    ("SO-24003", 1, "BAG-KRF-M", 2000, "1.95"),
    ("SO-24003", 2, "CUP-PET-500", 30, "62.50"),
    ("SO-24003", 3, "LID-DOME-95", 30, "38.00"),
    ("SO-24004", 1, "CNT-HNG-1L", 12, "575.00"),
    ("SO-24005", 1, "CUP-PET-500", 80, "61.00"),
    ("SO-24005", 2, "LID-DOME-95", 80, "37.50"),
]

BATCHES = [
    ("B-9001", "SO-24001", "BOX-CAKE-10", 400, datetime(2026, 9, 28, 14, 0)),
    ("B-9010", "SO-24002", "BOX-CAKE-10", 500, datetime(2026, 10, 9, 11, 30)),
    ("B-9011", "SO-24002", "BOX-CAKE-12", 120, datetime(2026, 10, 10, 9, 15)),
    ("B-9005", "SO-24005", "CUP-PET-500", 80, datetime(2026, 10, 3, 16, 0)),
    ("B-9006", "SO-24005", "LID-DOME-95", 80, datetime(2026, 10, 3, 16, 45)),
]

STOCK = [
    ("BOX-CAKE-10", "DBN-MAIN", 1800, 500),
    ("BOX-CAKE-12", "DBN-MAIN", 140, 120),
    ("BAG-KRF-M", "DBN-MAIN", 1200, 0),
    ("BAG-KRF-M", "PMB-DEPOT", 1500, 0),
    ("CUP-PET-500", "DBN-MAIN", 45, 0),
    ("LID-DOME-95", "DBN-MAIN", 60, 0),
    ("CNT-HNG-1L", "DBN-MAIN", 4, 0),
]

DISPATCHES = [
    ("D-5001", "SO-24001", datetime(2026, 10, 1, 7, 30), datetime(2026, 10, 1, 13, 5), "POD-77812"),
    ("D-5005", "SO-24005", datetime(2026, 10, 7, 8, 0), None, None),
]


def _insert(conn, table: Table, rows: list[tuple]) -> None:
    """Insert tuples in the table's column order (skipping an autoincrement id)."""
    columns = [c.name for c in table.columns if c.autoincrement is not True]
    conn.execute(table.insert(), [dict(zip(columns, row, strict=True)) for row in rows])


def seed(engine: Engine) -> None:
    metadata.drop_all(engine)
    metadata.create_all(engine)
    with engine.begin() as conn:
        _insert(conn, customers, CUSTOMERS)
        _insert(conn, products, PRODUCTS)
        _insert(conn, sales_orders, ORDERS)
        _insert(conn, order_lines, [(o, n, s, q, Decimal(p)) for o, n, s, q, p in LINES])
        _insert(conn, batches, BATCHES)
        _insert(conn, stock, STOCK)
        _insert(conn, dispatches, DISPATCHES)


if __name__ == "__main__":
    engine = get_engine()
    seed(engine)
    print(f"Seeded {engine.url.render_as_string(hide_password=True)}")
