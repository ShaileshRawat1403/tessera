# tessera-api

Turn messy curl commands and HTTP traces into a validated, secret-redacted API surface map.

`tessera-api` reads `.curl` / `.sh` files containing curl commands, parses each into a canonical `ApiRequest`, **redacts every secret at parse time**, profiles the API surface, and emits a catalog plus reports — including a redactions audit.

## Scope (v0.1)

This pack parses and canonicalizes. It does **not** execute HTTP requests. Live calling, batch execution, and streaming response capture are runtime concerns with network side effects and are intentionally deferred to a later version. v0.1 is the offline, side-effect-free "what does this API surface look like, and does it leak secrets" pass.

## Secret safety

Redaction happens before a value is ever written into an `ApiRequest`. The canonical records and every artifact hold only masked previews (a couple of leading characters plus a length, never the tail). Secrets are detected by:

- known secret header names (`Authorization`, `X-Api-Key`, `Cookie`, ...)
- known secret query parameter names (`api_key`, `token`, `access_token`, `signature`, ...)
- `-u user:pass` basic-auth flags
- secret-ish keys inside request bodies (`password`, `client_secret`, `token`, ...)
- **secret *shape* (v0.2)** — values that look like secrets regardless of field name: AWS keys (`AKIA…`), GitHub tokens (`ghp_…`), Slack/Stripe/Google/OpenAI keys, JWTs, private-key blocks, and high-entropy token strings. This catches secrets hiding in custom auth headers, odd query params, or body fields, and raises `secret_in_nonstandard_location` so you know a credential is somewhere unexpected. UUIDs and other common identifiers are excluded to avoid false positives.

## Compile an API pack

```bash
tessera api compile --input examples/api/ --output ./out/api_pack
```

Artifacts written:

```text
index.jsonl              canonical, redacted ApiRequest rows
index.md                 human-readable catalog (method, host, path, auth, redactions)
validation_report.md     hygiene findings
coverage_report.md       method / host / auth-kind distribution
redactions_report.md     every redaction made, with masked previews (audit trail)
```

## Validation rules

Per-request:

- `insecure_scheme` — uses `http://` (cleartext)
- `missing_host` — no host could be parsed
- `secret_in_url_query` — a secret was found in the URL query (URLs get logged; prefer a header)
- `no_auth_detected` — no auth credential was found

Cross-request:

- `duplicate_request` — identical method + url + body seen more than once
- `multiple_hosts` — requests span more than one host (visibility, not an error)

Plus `parse_error` for any curl command that cannot be tokenized or has no URL.
