# tesserakit-dockerfile

Lint Dockerfiles for image hygiene and security.

`tessera-dockerfile` parses Dockerfiles (handling line continuations and multi-stage builds), inventories their instructions, and flags common hygiene and security problems. No image is built and nothing is executed.

## Lint

```bash
tessera dockerfile lint --input . --output ./out/dockerfile_pack
tessera dockerfile lint --input Dockerfile --output ./out/dockerfile_pack
```

Recognizes `Dockerfile`, `Dockerfile.*`, and `*.dockerfile`.

Artifacts written:

```text
instructions.jsonl       one Instruction per parsed line (with build stage)
index.md                 instruction inventory + stage list
validation_report.md     hygiene + security findings
coverage_report.md       instruction frequency
```

## Lint rules

- `unpinned_base_image` — `FROM image` with no tag (implicitly `:latest`)
- `latest_tag` — `FROM image:latest`
- `runs_as_root` — no `USER` instruction; the container runs as root
- `secret_in_image` — `ENV`/`ARG` bakes a secret-named value into an image layer
- `add_instead_of_copy` — `ADD` used for local files (prefer `COPY`)
- `missing_healthcheck` — no `HEALTHCHECK` instruction (info)

Multi-stage builds are understood: a `FROM <stage>` that references an earlier `AS <stage>` is not flagged as an unpinned base image.
