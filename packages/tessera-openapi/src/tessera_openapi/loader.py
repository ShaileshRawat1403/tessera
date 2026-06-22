from __future__ import annotations

from pathlib import Path
from typing import Any

from tessera_openapi.schema import Endpoint, SpecInfo
from tessera_openapi.spec import (
    find_spec_file,
    iter_operations,
    load_spec,
    path_params_in,
    spec_version,
)


def load_openapi_records(input_path: Path, options: dict[str, Any]) -> list[Endpoint]:
    """Parse a spec into Endpoint records. Stashes SpecInfo + errors in options."""
    errors: list[dict[str, str]] = []
    spec_path = find_spec_file(input_path)
    if spec_path is None:
        options["_errors"] = [{"error": f"no OpenAPI/Swagger spec found at {input_path}"}]
        options["_info"] = SpecInfo()
        return []

    try:
        doc = load_spec(spec_path)
    except Exception as exc:
        options["_errors"] = [{"error": f"failed to parse {spec_path.name}: {exc}"}]
        options["_info"] = SpecInfo()
        return []

    if not isinstance(doc, dict) or ("openapi" not in doc and "swagger" not in doc):
        options["_errors"] = [{"error": f"{spec_path.name} is not an OpenAPI/Swagger document"}]
        options["_info"] = SpecInfo()
        return []

    has_global_security = bool(doc.get("security"))
    endpoints: list[Endpoint] = []

    for path, method, op, shared in iter_operations(doc):
        params = list(shared) + list(op.get("parameters", []) or [])
        declared_path_params = [
            str(p.get("name", "")) for p in params
            if isinstance(p, dict) and p.get("in") == "path"
        ]
        responses = [str(code) for code in (op.get("responses", {}) or {}).keys()]
        secured = bool(op.get("security")) or has_global_security

        endpoints.append(
            Endpoint(
                method=method.upper(),
                path=path,
                operation_id=str(op.get("operationId", "")),
                summary=str(op.get("summary", "") or op.get("description", "")),
                tags=[str(t) for t in (op.get("tags", []) or [])],
                path_params=path_params_in(path),
                declared_path_params=declared_path_params,
                has_request_body=bool(op.get("requestBody")) or any(
                    isinstance(p, dict) and p.get("in") == "body" for p in params
                ),
                responses=responses,
                deprecated=bool(op.get("deprecated", False)),
                secured=secured,
                metadata={"source_file": str(spec_path)},
            )
        )

    info = doc.get("info", {}) or {}
    options["_errors"] = errors
    options["_info"] = SpecInfo(
        title=str(info.get("title", "")),
        version=str(info.get("version", "")),
        spec_version=spec_version(doc),
        server_count=len(doc.get("servers", []) or []) or (1 if doc.get("host") else 0),
        endpoint_count=len(endpoints),
    )
    return endpoints
