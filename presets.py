"""Named text-normalization profiles used by the processing engine."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Callable

from exceptions import DataValidationError


@dataclass(frozen=True)
class NormalizationPreset:
    """A named transformation applied after common text sanitation."""

    name: str
    transform: Callable[[str], str]


def _collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def _strict_alpha(text: str) -> str:
    return _collapse_whitespace(re.sub(r"[^A-Za-z\s]", "", text))


def _financial_numeric(text: str) -> str:
    return _collapse_whitespace(re.sub(r"[^0-9.,+\-\s]", "", text))


def _slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode(
        "ascii", "ignore"
    ).decode("ascii")
    words = re.findall(r"[A-Za-z0-9]+", ascii_text.casefold())
    return "-".join(words)


def _alphanumeric_clean(text: str) -> str:
    return _collapse_whitespace(re.sub(r"[^A-Za-z0-9\s]", "", text))


PRESETS: dict[str, NormalizationPreset] = {
    "Strict Alpha": NormalizationPreset("Strict Alpha", _strict_alpha),
    "Financial/Numeric Only": NormalizationPreset(
        "Financial/Numeric Only", _financial_numeric
    ),
    "Slugify": NormalizationPreset("Slugify", _slugify),
    "Alphanumeric Clean": NormalizationPreset(
        "Alphanumeric Clean", _alphanumeric_clean
    ),
}


def get_preset(name: str) -> NormalizationPreset:
    """Return a configured preset or raise a contextual validation error."""
    try:
        return PRESETS[name]
    except (KeyError, TypeError) as error:
        raise DataValidationError(
            "Unknown normalization preset.", {"preset": name}
        ) from error