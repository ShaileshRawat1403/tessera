# tesserakit-sql

Lint SQL files and migrations into a statement and table catalog.

`tessera-sql` parses `.sql` files with lightweight heuristics (no database connection, no execution), builds a catalog of statements and declared tables, and flags high-signal migration-safety issues.

## Lint SQL

```bash
tessera sql lint --input migrations/ --output ./out/sql_pack
tessera sql lint --input schema.sql --output ./out/sql_pack
```

Artifacts written:

```text
statements.jsonl         one SqlStatement per parsed statement (kind, target, flags)
tables.jsonl             one SqlTable per CREATE TABLE (columns, primary-key flag)
index.md                 statement catalog
validation_report.md     safety findings
coverage_report.md       statement-kind distribution
tables.md                table catalog with columns and PK status
```

## Lint rules

Query safety:

- `delete_without_where` (error) — `DELETE` with no `WHERE` removes every row
- `update_without_where` (warning) — `UPDATE` with no `WHERE` writes every row
- `select_star` (info) — `SELECT *` couples the query to column shape

Migration safety (the costly, easy-to-miss class):

- `add_not_null_without_default` (error) — `ALTER TABLE ... ADD COLUMN ... NOT NULL` with no `DEFAULT` rewrites the table and fails on existing rows
- `truncate_table` (warning) — `TRUNCATE` wipes all rows and is often non-transactional / irreversible
- `drop_column` (warning) — dropping a column is destructive and irreversible
- `rename_breaks_compatibility` (warning) — `RENAME` breaks code referencing the old name; prefer add-new + backfill + drop-old
- `drop_without_if_exists` (warning) — `DROP` without `IF EXISTS` fails if the object is absent
- `create_table_without_if_not_exists` (info) — non-idempotent if the migration re-runs

Schema:

- `table_without_primary_key` (warning) — a `CREATE TABLE` declares no `PRIMARY KEY`
- `no_statements` — nothing parsed

## Limitations (v0.1)

Parsing is heuristic: comments are stripped, statements are split on top-level
semicolons (quote-aware), and classification is keyword/regex based. It is tuned
for migration and schema files, not for validating arbitrary vendor SQL dialects.
