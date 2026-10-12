-- PostgreSQL schema for the ERP demo. Mirrors src/erp_mcp/db.py.
-- Apply with: psql "$DATABASE_URL" -f sql/schema.sql

CREATE TABLE customers (
    code        varchar(10)  PRIMARY KEY,
    name        varchar(120) NOT NULL,
    region      varchar(40)  NOT NULL
);

CREATE TABLE products (
    sku         varchar(20)  PRIMARY KEY,
    description varchar(200) NOT NULL,
    unit        varchar(20)  NOT NULL
);

CREATE TABLE sales_orders (
    order_number  varchar(20) PRIMARY KEY,
    customer_code varchar(10) NOT NULL REFERENCES customers(code),
    customer_po   varchar(40) NOT NULL,
    order_date    date        NOT NULL,
    due_date      date        NOT NULL,
    status        varchar(20) NOT NULL
        CHECK (status IN ('draft', 'approved', 'in_production', 'dispatched', 'delivered', 'cancelled'))
);
CREATE INDEX sales_orders_open_idx ON sales_orders (due_date)
    WHERE status IN ('draft', 'approved', 'in_production');

CREATE TABLE order_lines (
    id           integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_number varchar(20)   NOT NULL REFERENCES sales_orders(order_number),
    line_no      integer       NOT NULL,
    sku          varchar(20)   NOT NULL REFERENCES products(sku),
    quantity     integer       NOT NULL CHECK (quantity > 0),
    unit_price   numeric(12,2) NOT NULL CHECK (unit_price >= 0),
    UNIQUE (order_number, line_no)
);
CREATE INDEX order_lines_sku_idx ON order_lines (sku);

CREATE TABLE batches (
    batch_number varchar(20) PRIMARY KEY,
    order_number varchar(20) NOT NULL REFERENCES sales_orders(order_number),
    sku          varchar(20) NOT NULL REFERENCES products(sku),
    quantity     integer     NOT NULL CHECK (quantity > 0),
    produced_at  timestamp
);
CREATE INDEX batches_order_idx ON batches (order_number);

CREATE TABLE stock (
    sku      varchar(20) NOT NULL REFERENCES products(sku),
    location varchar(20) NOT NULL,
    on_hand  integer     NOT NULL,
    reserved integer     NOT NULL CHECK (reserved >= 0),
    PRIMARY KEY (sku, location)
);

CREATE TABLE dispatches (
    dispatch_number varchar(20) PRIMARY KEY,
    order_number    varchar(20) NOT NULL REFERENCES sales_orders(order_number),
    dispatched_at   timestamp   NOT NULL,
    delivered_at    timestamp,
    pod_reference   varchar(40)
);
CREATE INDEX dispatches_order_idx ON dispatches (order_number);
