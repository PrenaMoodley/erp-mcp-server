# Changelog

## [Unreleased]

## [0.1.0] - 2026-10-12

### Added
- MCP server with five read-only tools: `find_customers`, `get_order`, `trace_order`, `stock_position`, `open_orders`.
- `erp://schema` resource.
- SQLAlchemy schema plus hand-written PostgreSQL `schema.sql` and a read-only database role.
- Fictional seed data for a packaging manufacturer.
- Claude Code setup: `CLAUDE.md`, `/add-tool` command, `sql-reviewer` subagent, `.mcp.json`.
- CI: tests on SQLite and PostgreSQL 17; schema and read-only role verified.
