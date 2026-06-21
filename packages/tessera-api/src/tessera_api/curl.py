"""Parse curl commands into canonical, redacted ApiRequest records."""

from __future__ import annotations

import shlex
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from tessera_api.redact import (
    auth_token_value,
    classify_header_secret,
    is_secret_header,
    is_secret_query,
    mask,
)
from tessera_api.schema import ApiAuth, ApiRequest, Redaction


def split_curl_commands(text: str) -> list[str]:
    """Split a file's text into individual curl command strings.

    Line continuations (trailing backslash) are joined first; then each block
    that begins with a ``curl`` token starts a new command.
    """
    joined = text.replace("\\\n", " ")
    commands: list[str] = []
    current: list[str] = []
    for raw_line in joined.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        starts = line.split(None, 1)[0] == "curl" if line.split() else False
        if starts and current:
            commands.append(" ".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        commands.append(" ".join(current))
    return [c for c in commands if c.strip().startswith("curl")]


def parse_curl(command: str, record_id: str) -> ApiRequest:
    """Parse a single curl command string into a redacted ApiRequest.

    Raises ValueError if the command cannot be tokenized or has no URL.
    """
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        raise ValueError(f"cannot tokenize curl command: {exc}") from exc

    if not tokens or tokens[0] != "curl":
        raise ValueError("not a curl command")

    method: str | None = None
    url: str | None = None
    headers: dict[str, str] = {}
    redactions: list[Redaction] = []
    auth = ApiAuth()
    body: str | None = None
    body_kind = "none"
    basic_user_pass: str | None = None

    i = 1
    while i < len(tokens):
        tok = tokens[i]
        if tok in ("-X", "--request"):
            method = tokens[i + 1] if i + 1 < len(tokens) else method
            i += 2
            continue
        if tok in ("-H", "--header"):
            raw = tokens[i + 1] if i + 1 < len(tokens) else ""
            _ingest_header(raw, headers, redactions, auth)
            i += 2
            continue
        if tok in ("-u", "--user"):
            basic_user_pass = tokens[i + 1] if i + 1 < len(tokens) else ""
            i += 2
            continue
        if tok in ("-d", "--data", "--data-raw", "--data-binary", "--data-ascii"):
            raw_body = tokens[i + 1] if i + 1 < len(tokens) else ""
            body_kind = "json" if _looks_json(raw_body) else "form"
            body, body_redactions = _redact_body(raw_body)
            redactions.extend(body_redactions)
            i += 2
            continue
        if tok in ("--url",):
            url = tokens[i + 1] if i + 1 < len(tokens) else url
            i += 2
            continue
        if tok in ("--compressed", "-s", "--silent", "-L", "--location", "-k", "--insecure", "-i", "--include", "-v", "--verbose", "-g", "--globoff"):
            i += 1
            continue
        if tok.startswith("-"):
            # Unknown flag; skip it and a value if the next token is not a URL.
            if i + 1 < len(tokens) and not _is_url(tokens[i + 1]) and not tokens[i + 1].startswith("-"):
                i += 2
            else:
                i += 1
            continue
        # positional: treat as URL
        if url is None and _is_url(tok):
            url = tok
        i += 1

    if url is None:
        raise ValueError("no URL found in curl command")

    # Basic auth via -u
    if basic_user_pass is not None:
        user = basic_user_pass.split(":", 1)[0]
        auth = ApiAuth(kind="basic", location="flag:-u", present=True)
        redactions.append(
            Redaction(location="flag:-u", kind="basic_credentials", preview=f"{mask(user)} : (password redacted)")
        )

    scheme, host, path, redacted_query, query_map, url_redactions = _split_and_redact_url(url)
    redactions.extend(url_redactions)

    # If a secret query param looks like auth and no header auth was found.
    if auth.kind == "none":
        for qname in query_map:
            if qname.lower() in ("api_key", "apikey", "key", "access_token", "token"):
                auth = ApiAuth(kind="api_key_query", location=f"query:{qname}", present=True)
                break

    if method is None:
        method = "POST" if body is not None else "GET"

    redacted_url = urlunsplit((scheme, host, path, redacted_query, ""))

    return ApiRequest(
        id=record_id,
        method=method.upper(),
        url=redacted_url,
        scheme=scheme,
        host=host,
        path=path,
        query=query_map,
        headers=headers,
        body=body,  # already redacted in the -d handler
        body_kind=body_kind,
        auth=auth,
        redactions=redactions,
        # Note: the raw command is never stored; it contains the unredacted
        # secrets we just stripped. Only a safe synthesized summary is kept.
        metadata={"summary": f"{method.upper()} {host}{path}"},
    )


def _ingest_header(raw: str, headers: dict[str, str], redactions: list[Redaction], auth: ApiAuth) -> None:
    if ":" not in raw:
        headers[raw.strip()] = ""
        return
    name, value = raw.split(":", 1)
    name = name.strip()
    value = value.strip()
    if is_secret_header(name):
        kind = classify_header_secret(name, value)
        cred = auth_token_value(value)
        redactions.append(Redaction(location=f"header:{name.lower()}", kind=kind, preview=mask(cred)))
        headers[name] = "(redacted)"
        if kind == "bearer_token":
            auth.kind = "bearer"
            auth.location = f"header:{name}"
            auth.present = True
        elif kind == "basic_credentials":
            auth.kind = "basic"
            auth.location = f"header:{name}"
            auth.present = True
        elif kind == "api_key":
            auth.kind = "api_key_header"
            auth.location = f"header:{name}"
            auth.present = True
    else:
        headers[name] = value


def _split_and_redact_url(url: str):
    parts = urlsplit(url)
    query_pairs = parse_qsl(parts.query, keep_blank_values=True)
    redactions: list[Redaction] = []
    redacted_pairs: list[tuple[str, str]] = []
    query_map: dict[str, str] = {}
    for k, v in query_pairs:
        if is_secret_query(k):
            redactions.append(Redaction(location=f"query:{k}", kind="api_key", preview=mask(v)))
            redacted_pairs.append((k, "(redacted)"))
            query_map[k] = "(redacted)"
        else:
            redacted_pairs.append((k, v))
            query_map[k] = v
    redacted_query = urlencode(redacted_pairs)
    return parts.scheme, parts.netloc, parts.path, redacted_query, query_map, redactions


def _redact_body(body: str) -> tuple[str, list[Redaction]]:
    """Redact secret-keyed fields in a JSON-ish or form body, reporting each.

    Returns the redacted body and a Redaction per field masked, so body
    secrets appear in the audit trail like header and query secrets do.
    """
    import re

    redactions: list[Redaction] = []
    secret_keys = r"password|passwd|pwd|secret|client_secret|token|access_token|api_key|apikey"

    def json_sub(m: "re.Match[str]") -> str:
        key, value = m.group(1), m.group(3)
        redactions.append(Redaction(location=f"body:{key.lower()}", kind="body_secret", preview=mask(value)))
        return f'{m.group(2)}(redacted)"'

    def form_sub(m: "re.Match[str]") -> str:
        key, value = m.group(1), m.group(2)
        redactions.append(Redaction(location=f"body:{key.lower()}", kind="body_secret", preview=mask(value)))
        return f"{key}=(redacted)"

    redacted = re.sub(
        rf'"({secret_keys})"(\s*:\s*")([^"]*)"',
        json_sub,
        body,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(
        rf"\b({secret_keys})=([^&\s]+)",
        form_sub,
        redacted,
        flags=re.IGNORECASE,
    )
    return redacted, redactions


def _looks_json(body: str) -> bool:
    s = body.strip()
    return s.startswith("{") or s.startswith("[")


def _is_url(token: str) -> bool:
    return token.startswith("http://") or token.startswith("https://")
