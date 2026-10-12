-- A login role for the MCP server that can read and nothing else.
-- The server's code only runs SELECTs, but the database should enforce that too:
-- if a bug or a prompt injection ever produced a write, PostgreSQL refuses it.
--
-- Run as the database owner. Replace the password, and keep the real one in a
-- secrets manager, never in this repository.

CREATE ROLE erp_mcp_readonly LOGIN PASSWORD 'change-me';

GRANT CONNECT ON DATABASE erp TO erp_mcp_readonly;
GRANT USAGE ON SCHEMA public TO erp_mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO erp_mcp_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO erp_mcp_readonly;

-- Belt and braces: every session for this role is read-only and short-lived.
ALTER ROLE erp_mcp_readonly SET default_transaction_read_only = on;
ALTER ROLE erp_mcp_readonly SET statement_timeout = '5s';
