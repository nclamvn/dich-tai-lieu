"""Stable, round-trippable serialization for the document AST (L0).

The DocumentAST is the single source of truth every renderer reads from. This
module gives it a JSON-safe interchange form so it can be cached, logged,
diffed, or handed between stages with the guarantee:

    ast_from_dict(ast_to_dict(doc)) == doc
    ast_from_json(ast_to_json(doc)) == doc

The encoding is tagged (``__enum__`` / ``__dc__``) so enums and nested
dataclasses survive the round trip, and it auto-discovers every Enum and
dataclass defined in ``document_ast`` — new block types serialize with zero
changes here. The derived ``block_type`` field is never serialized; it is
restored by each block's ``__post_init__``.
"""

from __future__ import annotations

import dataclasses
import json
from enum import Enum
from typing import Any, Optional

from core.rendering import document_ast as _ast

# Auto-registry of serializable types, keyed by class name.
_ENUMS = {
    name: obj
    for name, obj in vars(_ast).items()
    if isinstance(obj, type) and issubclass(obj, Enum)
}
_DATACLASSES = {
    name: obj
    for name, obj in vars(_ast).items()
    if isinstance(obj, type) and dataclasses.is_dataclass(obj)
}

# Derived (set in __post_init__) — never serialized or restored by constructor.
_DERIVED = {"block_type"}


def _encode(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return {"__enum__": type(obj).__name__, "value": obj.value}
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {
            "__dc__": type(obj).__name__,
            "fields": {
                f.name: _encode(getattr(obj, f.name))
                for f in dataclasses.fields(obj)
                if f.name not in _DERIVED
            },
        }
    if isinstance(obj, (list, tuple)):
        return [_encode(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _encode(v) for k, v in obj.items()}
    return obj


def _decode(obj: Any) -> Any:
    if isinstance(obj, dict):
        if "__enum__" in obj:
            return _ENUMS[obj["__enum__"]](obj["value"])
        if "__dc__" in obj:
            cls = _DATACLASSES[obj["__dc__"]]
            raw = {k: _decode(v) for k, v in obj["fields"].items()}
            init_names = {f.name for f in dataclasses.fields(cls) if f.init}
            instance = cls(**{k: v for k, v in raw.items() if k in init_names})
            # Restore stateful non-init fields (e.g. `style`); skip derived ones.
            for key, value in raw.items():
                if key not in init_names and key not in _DERIVED:
                    setattr(instance, key, value)
            return instance
        return {k: _decode(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decode(x) for x in obj]
    return obj


def ast_to_dict(document: Any) -> Any:
    """Serialize a DocumentAST (or any AST block) to a JSON-safe structure."""
    return _encode(document)


def ast_from_dict(data: Any) -> Any:
    """Rebuild a DocumentAST (or block) from ``ast_to_dict`` output."""
    return _decode(data)


def ast_to_json(document: Any, indent: Optional[int] = None) -> str:
    return json.dumps(_encode(document), ensure_ascii=False, indent=indent)


def ast_from_json(text: str) -> Any:
    return _decode(json.loads(text))
