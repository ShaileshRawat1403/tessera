-- Sample schema + migration with a mix of safe and risky statements.

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    active BOOLEAN DEFAULT true
);

-- no primary key on purpose
CREATE TABLE logs (
    message TEXT,
    created_at TIMESTAMP
);

CREATE INDEX idx_users_email ON users (email);

-- dangerous: no WHERE
DELETE FROM sessions;

-- dangerous: no WHERE
UPDATE users SET active = false;

-- risky: no IF EXISTS
DROP TABLE temp_data;

-- fine: scoped delete
DELETE FROM sessions WHERE created_at < '2020-01-01';

-- fine: guarded drop
DROP TABLE IF EXISTS scratch;

-- info: select star
SELECT * FROM users;

-- migration-safety cases ----------------------------------------------------

-- locking rewrite: NOT NULL with no DEFAULT on an existing table
ALTER TABLE users ADD COLUMN phone TEXT NOT NULL;

-- safe add: has a DEFAULT, so existing rows are fine
ALTER TABLE users ADD COLUMN nickname TEXT DEFAULT '';

-- destructive: column drop
ALTER TABLE users DROP COLUMN active;

-- breaking: rename
ALTER TABLE logs RENAME TO audit_logs;

-- destructive bulk wipe
TRUNCATE TABLE audit_logs;

-- idempotent create (should NOT trigger the if-not-exists info)
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY,
    key TEXT
);
