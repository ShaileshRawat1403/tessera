# tesserakit-config

Inventory a project's configuration, check for leaked secrets, and report config drift.

`tessera-config` scans env files and source code, aggregates every configuration key, **redacts secret values at load time**, and reports the gaps between what is documented, what is set, and what is actually used. No code is executed and no network calls are made.

## What it scans

- **Real env files** (`.env`, `.env.local`, ...) → keys and (redacted) values.
- **Example files** (`.env.example`, `.env.sample`, `.env.template`) → documented keys.
- **Source code** (`.py`, `.js`, `.ts`, `.rb`, `.go`, ...) → env-var references:
  `os.getenv("X")`, `os.environ["X"]`, `os.environ.get("X")`, `getenv("X")`,
  `process.env.X`, `process.env["X"]`.

## Secret safety

Values for secret-named keys (`*TOKEN*`, `*SECRET*`, `*PASSWORD*`, `*API_KEY*`,
`*CREDENTIAL*`, ...) are masked before any record or artifact is written. The
inventory shows `(set)` for non-secret values and a masked preview for secret
ones; the raw value never leaves the source file.

## Audit a project

```bash
tessera config audit --input . --output ./out/config_pack
```

Artifacts written:

```text
config_inventory.jsonl   one ConfigKey per key (env/example/code flags, masked value)
index.md                 the inventory table
validation_report.md     findings (leaked secrets, drift)
coverage_report.md       documented %, used %, secret count
drift_report.md          used-but-undocumented / set-but-undocumented / documented-but-unused
```

## Validation rules

- `possible_committed_secret` — a secret-named key has a value in a real `.env`
- `secret_value_in_nonsecret_key` — a value *shaped* like a secret (e.g. `MY_THING=ghp_…`) under a key whose name isn't secret-like; name-based detection alone would miss it
- `missing_in_example` — used in code but not documented in any `.env.example`
- `undocumented_env_key` — set in `.env` but not in any example
- `unused_documented_key` — documented in an example but never used or set
- `no_config_keys` — nothing found

Secret detection screens values by shape (AWS/GitHub/Slack/Stripe/JWT/etc. + a conservative high-entropy heuristic) in addition to key names, with UUIDs excluded.
