import asyncio
import json
import os

import pytest

from erp_mcp import queries, server
from erp_mcp.db import get_engine
from erp_mcp.seed import seed


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    # CI sets TEST_DATABASE_URL to a real PostgreSQL service; locally we use SQLite.
    url = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tmp_path_factory.mktemp('db') / 'erp.db'}"
    engine = get_engine(url)
    seed(engine)
    return engine


def test_find_customers_by_name_and_code(engine):
    assert [c["code"] for c in queries.find_customers(engine, "coastal")] == ["C1001"]
    assert [c["code"] for c in queries.find_customers(engine, "c1003")] == ["C1003"]


def test_find_customers_treats_wildcards_literally(engine):
    assert queries.find_customers(engine, "%") == []
    assert queries.find_customers(engine, "_") == []


def test_get_order_totals_in_decimal(engine):
    order = queries.get_order(engine, "SO-24003")
    assert order["customer_name"] == "Berea Fresh Markets CC"
    assert [line["line_total"] for line in order["lines"]] == ["3900.00", "1875.00", "1140.00"]
    assert order["total_excl_vat"] == "6915.00"


def test_get_order_not_found(engine):
    with pytest.raises(queries.NotFound):
        queries.get_order(engine, "SO-00000")


def test_trace_delivered_order(engine):
    steps = [e["step"] for e in queries.trace_order(engine, "SO-24001")["events"]]
    assert steps == ["customer_po", "sales_order", "batch", "dispatch", "delivered"]


def test_trace_reports_production_shortfall(engine):
    trace = queries.trace_order(engine, "SO-24002")
    assert trace["production_shortfalls"] == [{"sku": "BOX-CAKE-12", "ordered": 250, "produced": 120}]


def test_stock_position_includes_open_demand(engine):
    pos = queries.stock_position(engine, "BAG-KRF-M")
    assert pos["total_available"] == 2700
    assert pos["open_order_demand"] == 2000


def test_open_orders_filters(engine):
    all_open = queries.open_orders(engine)
    assert [o["order_number"] for o in all_open] == ["SO-24004", "SO-24003", "SO-24002"]
    assert [o["order_number"] for o in queries.open_orders(engine, customer_code="C1001")] == ["SO-24002"]
    assert [o["order_number"] for o in queries.open_orders(engine, due_before="2026-10-15")] == ["SO-24004"]


def test_mcp_server_exposes_read_only_tools(engine, monkeypatch):
    monkeypatch.setattr(server, "engine", engine)

    async def run():
        tools = await server.mcp.list_tools()
        result = await server.mcp.call_tool("get_order", {"order_number": "SO-404"})
        return tools, result

    tools, result = asyncio.run(run())
    assert {t.name for t in tools} == {
        "find_customers",
        "get_order",
        "trace_order",
        "stock_position",
        "open_orders",
    }
    assert all(t.annotations.read_only_hint for t in tools)
    assert json.loads(result.content[0].text) == {"error": "No sales order SO-404"}
