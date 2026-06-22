"""Detect license identity from text and classify it."""

from __future__ import annotations

import re

# category by SPDX-ish id
CATEGORY = {
    "MIT": "permissive",
    "BSD-2-Clause": "permissive",
    "BSD-3-Clause": "permissive",
    "Apache-2.0": "permissive",
    "ISC": "permissive",
    "Unlicense": "public-domain",
    "CC0-1.0": "public-domain",
    "MPL-2.0": "weak-copyleft",
    "LGPL-3.0": "weak-copyleft",
    "LGPL-2.1": "weak-copyleft",
    "GPL-2.0": "copyleft",
    "GPL-3.0": "copyleft",
    "AGPL-3.0": "copyleft",
}

# ordered signatures: (id, regex over license text / declared value)
_SIGNATURES: list[tuple[str, re.Pattern]] = [
    ("AGPL-3.0", re.compile(r"GNU AFFERO GENERAL PUBLIC LICENSE|\bAGPL", re.IGNORECASE)),
    ("LGPL-3.0", re.compile(r"GNU LESSER GENERAL PUBLIC LICENSE|\bLGPL", re.IGNORECASE)),
    ("GPL-3.0", re.compile(r"GNU GENERAL PUBLIC LICENSE.*Version 3|GPL-3|GPLv3", re.IGNORECASE | re.DOTALL)),
    ("GPL-2.0", re.compile(r"GNU GENERAL PUBLIC LICENSE.*Version 2|GPL-2|GPLv2", re.IGNORECASE | re.DOTALL)),
    ("Apache-2.0", re.compile(r"Apache License.*Version 2\.0|Apache-2", re.IGNORECASE | re.DOTALL)),
    ("MPL-2.0", re.compile(r"Mozilla Public License.*2\.0|MPL-2", re.IGNORECASE | re.DOTALL)),
    ("BSD-3-Clause", re.compile(r"Redistribution and use.*Neither the name|BSD-3", re.IGNORECASE | re.DOTALL)),
    ("BSD-2-Clause", re.compile(r"Redistribution and use|BSD-2", re.IGNORECASE | re.DOTALL)),
    ("ISC", re.compile(r"\bISC License|Permission to use, copy, modify, and/or distribute", re.IGNORECASE)),
    ("Unlicense", re.compile(r"This is free and unencumbered software released into the public domain|Unlicense", re.IGNORECASE)),
    ("CC0-1.0", re.compile(r"CC0 1\.0|Creative Commons.*CC0", re.IGNORECASE)),
    ("MIT", re.compile(r"\bMIT License|Permission is hereby granted, free of charge", re.IGNORECASE)),
]


def detect_from_text(text: str) -> str:
    head = text[:4000]
    for license_id, pat in _SIGNATURES:
        if pat.search(head):
            return license_id
    return "unknown"


def normalize_declared(value: str) -> str:
    """Normalize a manifest 'license' value to an SPDX-ish id."""
    v = value.strip()
    # exact-ish matches
    direct = {
        "mit": "MIT", "apache-2.0": "Apache-2.0", "apache 2.0": "Apache-2.0",
        "bsd": "BSD-3-Clause", "bsd-3-clause": "BSD-3-Clause", "bsd-2-clause": "BSD-2-Clause",
        "isc": "ISC", "mpl-2.0": "MPL-2.0", "gpl-3.0": "GPL-3.0", "gpl-3.0-only": "GPL-3.0",
        "gpl-2.0": "GPL-2.0", "agpl-3.0": "AGPL-3.0", "lgpl-3.0": "LGPL-3.0",
        "unlicense": "Unlicense", "cc0-1.0": "CC0-1.0",
    }
    low = v.lower()
    if low in direct:
        return direct[low]
    # fall back to text detection on the declared value
    return detect_from_text(v)


def category_for(license_id: str) -> str:
    return CATEGORY.get(license_id, "unknown")
