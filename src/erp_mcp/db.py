"""Database schema for a small manufacturing ERP.

Defined with SQLAlchemy Core so the same tables run on PostgreSQL in production
and on SQLite for tests and the offline demo. `sql/schema.sql` is the hand-written
PostgreSQL version of the same schema.
"""

from __future__ import annotations

import os

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.engine import Engine

metadata = MetaData()

customers = Table(
    "customers",
    metadata,
    Column("code", String(10), primary_key=True),
    Column("name", String(120), nullable=False),
    Column("region", String(40), nullable=False),
)

products = Table(
    "products",
    metadata,
    Column("sku", String(20), primary_key=True),
    Column("description", String(200), nullable=False),
    Column("unit", String(20), nullable=False),
)

sales_orders = Table(
    "sales_orders",
    metadata,
    Column("order_number", String(20), primary_key=True),
    Column("customer_code", ForeignKey("customers.code"), nullable=False),
    Column("customer_po", String(40), nullable=False),
    Column("order_date", Date, nullable=False),
    Column("due_date", Date, nullable=False),
    # draft -> approved -> in_production -> dispatched -> delivered | cancelled
    Column("status", String(20), nullable=False),
)

order_lines = Table(
    "order_lines",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("order_number", ForeignKey("sales_orders.order_number"), nullable=False),
    Column("line_no", Integer, nullable=False),
    Column("sku", ForeignKey("products.sku"), nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("unit_price", Numeric(12, 2), nullable=False),
    UniqueConstraint("order_number", "line_no"),
)

batches = Table(
    "batches",
    metadata,
    Column("batch_number", String(20), primary_key=True),
    Column("order_number", ForeignKey("sales_orders.order_number"), nullable=False),
    Column("sku", ForeignKey("products.sku"), nullable=False),
    Column("quantity", Integer, nullable=False),
    Column("produced_at", DateTime),
)

stock = Table(
    "stock",
    metadata,
    Column("sku", ForeignKey("products.sku"), primary_key=True),
    Column("location", String(20), primary_key=True),
    Column("on_hand", Integer, nullable=False),
    Column("reserved", Integer, nullable=False),
)

dispatches = Table(
    "dispatches",
    metadata,
    Column("dispatch_number", String(20), primary_key=True),
    Column("order_number", ForeignKey("sales_orders.order_number"), nullable=False),
    Column("dispatched_at", DateTime, nullable=False),
    Column("delivered_at", DateTime),
    Column("pod_reference", String(40)),  # proof of delivery document
)


def get_engine(url: str | None = None) -> Engine:
    url = url or os.environ.get("DATABASE_URL", "sqlite:///erp_demo.db")
    return create_engine(url)
