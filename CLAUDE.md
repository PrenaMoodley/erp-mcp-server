# erp-mcp-server

A read-only MCP server over a manufacturing ERP database (PostgreSQL in
production, SQLite for tests and the demo). Claude uses it to answer questions
about orders, production batches, stock and deliveries.

## Commands

- Install: `pip install -e ".[dev]"`
- Demo data: `python -m erp_mcp.seed` (creates `erp_demo.db`)
- Test: `python -m pytest -q` (SQLite; set `TEST_DATABASE_URL` to test on PostgreSQL)
- Lint: `python -m ruff check . && python -m ruff format --check .`
- Run the server: `python -m erp_mcp.server` (stdio; Claude Code starts it via `.mcp.json`)

## Rules

- **Read-only.** No tool may write. The database role in `sql/readonly_role.sql`
  enforces this too, but the code must not rely on that alone.
- **No raw SQL tool.** Every tool is a fixed, parameterised query. Do not add a
  "run any SELECT" tool; it bypasses row limits and exposes the whole schema.
- Queries live in `queries.py` as plain functions; `server.py` only wires them up.
- Return `{"error": ...}` for not-found cases so the model gets a usable answer.
- Money is `Decimal`, calculated in Python. Keep queries portable across PostgreSQL and SQLite.
- Schema changes go in both `db.py` and `sql/schema.sql`.
- All data in `seed.py` is fictional.

## Workflow

- New tool: `/add-tool <question it answers>`
- Before committing query or schema changes: run the `sql-reviewer` subagent.
