"""Strict JSON decoding for reviewed and native agent data."""

import json
from typing import Never

type JsonObject = dict[str, object]


class StrictJsonError(ValueError):
    """JSON uses an ambiguous or non-standard construct."""


def _unique_object(pairs: list[tuple[str, object]]) -> JsonObject:
    result: JsonObject = {}
    for key, value in pairs:
        if key in result:
            raise StrictJsonError("duplicate JSON object key")
        result[key] = value
    return result


def _non_finite_constant(_value: str) -> Never:
    raise StrictJsonError("non-finite JSON value")


def strict_json_loads(source: str | bytes) -> object:
    """Decode JSON while rejecting duplicate keys and non-finite constants."""
    return json.loads(
        source,
        object_pairs_hook=_unique_object,
        parse_constant=_non_finite_constant,
    )
