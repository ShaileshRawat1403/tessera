# tesserakit-openapi

Lint an OpenAPI/Swagger spec into a validated endpoint catalog.

`tessera-openapi` parses an OpenAPI 3.x or Swagger 2.0 document, builds a canonical `Endpoint` catalog, and lints for common spec-hygiene problems. It reads the spec only: nothing is fetched and no requests are made. It pairs naturally with `tessera-api` (curl traces in, spec quality out).

## Input

A spec file (`.json` / `.yaml` / `.yml`) or a directory containing one (it looks for `openapi.*` / `swagger.*`, then any yaml/json that mentions `openapi`/`swagger`).

## Lint a spec

```bash
tessera openapi lint --input examples/openapi/petstore.yaml --output ./out/openapi_pack
```

Artifacts written:

```text
endpoints.jsonl          one Endpoint per operation (method, path, params, responses, ...)
index.md                 endpoint catalog table
validation_report.md     lint findings
coverage_report.md       operationId / summary / security coverage, method distribution
surface.md               the API surface grouped by tag
```

## Lint rules

- `invalid_spec` — not parseable / not an OpenAPI document
- `no_endpoints` — the spec declares no operations
- `duplicate_operation_id` — two operations share an `operationId`
- `missing_operation_id` — an operation has no `operationId`
- `path_param_not_declared` — `{param}` in the path is not declared in `parameters`
- `declared_param_not_in_path` — a `path` parameter is declared but absent from the path template
- `missing_2xx_response` — no success (2xx/default) response is defined
- `missing_summary`, `no_tags`, `no_security`, `deprecated_endpoint` (informational)

Both OpenAPI 3.x (`requestBody`, `servers`) and Swagger 2.0 (`in: body` params, `host`) are handled.
