from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from math import isfinite
from numbers import Integral, Real
from typing import Any

import pandas as pd


def normalize_identifier(value: Any) -> str | None:
    """Preserve identifiers as strings; remove only surrounding whitespace."""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, Integral) and not isinstance(value, bool):
        return str(int(value))
    if isinstance(value, Real) and not isinstance(value, bool):
        if isfinite(float(value)) and float(value).is_integer():
            return str(int(value))
    if isinstance(value, Decimal) and value.is_finite() and value == value.to_integral_value():
        return str(int(value))
    text = str(value).strip()
    return text or None


def normalize_date(value: Any) -> date | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        parsed = pd.to_datetime(value, errors="raise")
        return parsed.date()
    except (ValueError, TypeError, OverflowError):
        return None


def normalize_amount(value: Any) -> Decimal | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    if isinstance(value, Decimal):
        return value
    text = str(value).strip().replace("$", "").replace(",", "")
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    try:
        amount = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if not amount.is_finite():
        return None
    return -amount if negative else amount
