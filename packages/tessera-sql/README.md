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

- `delete_without_where` (error) — `DELETE` with no `WHERE` removes every row
- `update_without_where` (warning) — `UPDATE` with no `WHERE` writes every row
- `drop_without_if_exists` (warning) — `DROP` without `IF EXISTS` fails if the object is absent
- `table_without_primary_key` (warning) — a `CREATE TABLE` declares no `PRIMARY KEY`
- `select_star` (info) — `SELECT *` couples the query to column shape
- `no_statements` — nothing parsed

## Limitations (v0.1)

Parsing is heuristic: comments are stripped, statements are split on top-level
semicolons (quote-aware), and classification is keyword/regex based. It is tuned
for migration and schema files, not for validating arbitrary vendor SQL dialects.
