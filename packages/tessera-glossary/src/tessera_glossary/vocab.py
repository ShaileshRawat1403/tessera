"""Tokenization, stopwords, and abbreviation knowledge for vocabulary analysis."""

from __future__ import annotations

import re

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# split an identifier into sub-words across snake_case, kebab, and camelCase
_SUBWORD_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]+")

STOPWORDS = {
    # english
    "the", "and", "for", "with", "not", "are", "was", "has", "have", "can",
    "will", "you", "your", "use", "used", "using", "into", "when", "then",
    "this", "that", "these", "those", "from", "out", "all", "any", "but",
    "its", "our", "their", "his", "her", "they", "them", "what", "which",
    "who", "why", "how", "where", "here", "there", "than", "such", "via",
    # programming keywords / very generic verbs
    "def", "class", "return", "import", "self", "cls", "true", "false",
    "none", "null", "var", "let", "const", "function", "public", "private",
    "static", "void", "int", "str", "bool", "list", "dict", "set", "get",
    "add", "new", "run", "is", "as", "if", "or", "in", "on", "at", "by",
    "to", "of", "do", "be", "we", "it", "an", "a", "type", "value", "name",
    "data", "item", "items", "result", "results", "test", "tests",
}


def tokenize_identifier(ident: str) -> list[str]:
    out: list[str] = []
    for part in _SUBWORD_RE.findall(ident):
        w = part.lower()
        if len(w) >= 3 and not w.isdigit() and w not in STOPWORDS:
            out.append(w)
    return out


def identifiers_in(text: str) -> list[str]:
    return _IDENT_RE.findall(text)


def words_in(text: str) -> list[str]:
    out: list[str] = []
    for w in _WORD_RE.findall(text.lower()):
        if len(w) >= 3 and w not in STOPWORDS:
            out.append(w)
    return out


# abbreviation -> canonical full word
ABBREVIATIONS = {
    "cfg": "config", "conf": "config", "config": "config", "configuration": "config",
    "msg": "message", "message": "message",
    "btn": "button", "button": "button",
    "repo": "repository", "repository": "repository",
    "num": "number", "number": "number",
    "ctx": "context", "context": "context",
    "db": "database", "database": "database",
    "auth": "authentication", "authentication": "authentication",
    "idx": "index", "index": "index",
    "tmp": "temporary", "temp": "temporary", "temporary": "temporary",
    "err": "error", "error": "error",
    "req": "request", "request": "request",
    "res": "response", "resp": "response", "response": "response",
    "usr": "user", "user": "user",
    "addr": "address", "address": "address",
    "calc": "calculate", "calculate": "calculate",
    "util": "utility", "utils": "utility", "utility": "utility",
    "doc": "documentation", "docs": "documentation", "documentation": "documentation",
    "img": "image", "image": "image",
    "fn": "function", "func": "function",
    "arg": "argument", "args": "argument", "argument": "argument",
    "param": "parameter", "params": "parameter", "parameter": "parameter",
    "env": "environment", "environment": "environment",
    "dir": "directory", "directory": "directory",
    "src": "source", "source": "source",
    "dest": "destination", "dst": "destination", "destination": "destination",
    "prev": "previous", "previous": "previous",
    "curr": "current", "current": "current",
    "info": "information", "information": "information",
    "spec": "specification", "specification": "specification",
}
