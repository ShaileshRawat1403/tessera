# tesserakit-schema

Catalog and lint JSON Schema documents.

`tessera-schema` discovers JSON Schema files, extracts their structure (`$id`, dialect, type, properties, required, `$defs`), and flags structural problems. It reads schemas only: no validation of instance data, no network.

## Lint

```bash
tessera schema lint --input schemas/ --output ./out/schema_pack
tessera schema lint --input person.schema.json --output ./out/schema_pack
```

A JSON file is treated as a schema when it has `$schema`, `properties`, `$defs`/`definitions`, or a schema-style root `type`. Common non-schema files (`package.json`, `tsconfig.json`, ...) are skipped.

Artifacts written:

```text
schemas.jsonl            one SchemaDoc per schema (type, properties, required, defs)
index.md                 the schema catalog
validation_report.md     structural findings
coverage_report.md       root-type distribution + title/$schema coverage
```

## Findings

- `required_not_in_properties` (error) — a `required` field is not declared in `properties`
- `missing_type` (warning) — root schema has no `type`
- `object_without_properties` (warning) — `type: object` with no `properties`
- `additional_properties_unset` (info) — `additionalProperties` not set; the object is open by default
- `missing_schema_version` (info) — no `$schema` dialect
- `missing_title` (info)
- `parse_error`, `no_schemas`
