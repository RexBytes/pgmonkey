-- pgmonkey test harness: database initialization
-- Runs inside each PostgreSQL container on first start.

-- Create test user with scram-sha-256 password
CREATE USER pgmonkey_user WITH PASSWORD 'pgmonkey_pass';

-- Grant access to the test database (created by POSTGRES_DB env var)
GRANT ALL PRIVILEGES ON DATABASE pgmonkey_test TO pgmonkey_user;

-- Switch to test database
\c pgmonkey_test

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO pgmonkey_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO pgmonkey_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO pgmonkey_user;

-- Test table for CSV export and general queries
CREATE TABLE test_data (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    value INTEGER NOT NULL,
    category VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO test_data (name, value, category) VALUES
    ('alpha',   100, 'group_a'),
    ('beta',    200, 'group_a'),
    ('gamma',   300, 'group_b'),
    ('delta',   400, 'group_b'),
    ('epsilon', 500, 'group_c');

GRANT ALL ON TABLE test_data TO pgmonkey_user;
GRANT USAGE, SELECT ON SEQUENCE test_data_id_seq TO pgmonkey_user;

-- Table for transaction tests (starts empty)
CREATE TABLE transaction_test (
    id SERIAL PRIMARY KEY,
    data VARCHAR(100)
);

GRANT ALL ON TABLE transaction_test TO pgmonkey_user;
GRANT USAGE, SELECT ON SEQUENCE transaction_test_id_seq TO pgmonkey_user;
