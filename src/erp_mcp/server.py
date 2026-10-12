"""MCP server: read-only access to ERP orders, production and stock.

Connect it to Claude Code (see .mcp.json) or Claude Desktop, then ask things like
"Which open orders for Coastal Bakeries are due this week, and do we have the stock?"

Run directly:  python -m erp_mcp.server
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from . import queries
from .db import get_engine

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)

mcp = MCPServer(
    name="erp",
    instructions=(
        "Read-only access to a manufacturing ERP: customers, sales orders, production "
        "batches, stock and dispatches. Use find_customers to resolve a customer name "
        "to a code before filtering by customer. Amounts are ZAR excluding VAT."
    ),
)
engine = get_engine()


def _not_found(e: queries.NotFound) -> dict:
    # Returned, not raised: the model gets a clear message it can act on.
    return {"error": str(e)}


@mcp.tool(annotations=READ_ONLY)
def find_customers(text: str) -> list[dict]:
    """Search customers by part of their name or account code."""
    return queries.find_customers(engine, text)


@mcp.tool(annotations=READ_ONLY)
def get_order(order_number: str) -> dict:
    """A sales order with its lines, customer and total excluding VAT."""
    try:
        return queries.get_order(engine, order_number)
    except queries.NotFound as e:
        return _not_found(e)


@mcp.tool(annotations=READ_ONLY)
def trace_order(order_number: str) -> dict:
    """Follow one order end to end: customer PO, sales order, production batches,
    dispatch and proof of delivery. Also lists SKUs not yet fully produced."""
    try:
        return queries.trace_order(engine, order_number)
    except queries.NotFound as e:
        return _not_found(e)


@mcp.tool(annotations=READ_ONLY)
def stock_position(sku: str) -> dict:
    """Stock on hand, reserved and available per location for one SKU, plus
    the quantity still needed by open orders."""
    try:
        return queries.stock_position(engine, sku)
    except queries.NotFound as e:
        return _not_found(e)


@mcp.tool(annotations=READ_ONLY)
def open_orders(customer_code: str | None = None, due_before: str | None = None) -> list[dict]:
    """Open sales orders (draft, approved or in production), soonest due first.
    Optionally filter by customer code and by due date (YYYY-MM-DD, exclusive)."""
    return queries.open_orders(engine, customer_code, due_before)


@mcp.resource("erp://schema", mime_type="text/markdown")
def schema() -> str:
    """How the ERP tables relate, for context."""
    return (
        "# ERP data model\n"
        "- customers(code, name, region)\n"
        "- sales_orders(order_number, customer_code, customer_po, order_date, due_date, status)\n"
        "  status: draft -> approved -> in_production -> dispatched -> delivered | cancelled\n"
        "- order_lines(order_number, line_no, sku, quantity, unit_price)\n"
        "- batches(batch_number, order_number, sku, quantity, produced_at)\n"
        "- stock(sku, location, on_hand, reserved)\n"
        "- dispatches(dispatch_number, order_number, dispatched_at, delivered_at, pod_reference)\n"
    )


def main() -> None:
    mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
