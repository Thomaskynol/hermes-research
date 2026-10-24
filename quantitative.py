#!/usr/bin/env python3
"""Reproducible local calculations for the research report (stdlib only).

Closed set of operations — never ``eval``. Every result keeps formula id,
validated inputs, units, assumptions, numeric result, timestamp and the source
URLs that back the inputs, so the report can be replayed bit for bit.

Errors are explicit ``ValueError``; NaN/Inf never leave this module silently.
"""
from __future__ import annotations

import math
import time

OPS = ("sum", "mean", "median", "min", "max", "percent_change", "ratio",
       "weighted_mean", "compound_growth", "unit_convert")

#: Only declared quantities are convertible (no currency: rates vary by date).
_UNITS = {
    "length": {"m": 1.0, "km": 1000.0, "cm": 0.01, "mm": 0.001,
               "mi": 1609.344, "ft": 0.3048, "in": 0.0254},
    "mass": {"kg": 1.0, "g": 0.001, "mg": 1e-06, "lb": 0.45359237,
             "oz": 0.028349523125},
    "data": {"B": 1.0, "KB": 1000.0, "MB": 1e06, "GB": 1e09, "TB": 1e12,
             "KiB": 1024.0, "MiB": 1048576.0, "GiB": 1073741824.0},
    "time": {"s": 1.0, "min": 60.0, "h": 3600.0, "day": 86400.0},
}


def _utcnow() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _number(value, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"[QUANT] {where} must be a finite number, "
                         f"got {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"[QUANT] {where} is not finite: {value!r}")
    return number


def _values(spec: dict, where: str = "values") -> list[float]:
    raw = spec.get(where)
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"[QUANT] {where} must be a non-empty list of numbers")
    return [_number(v, f"{where}[{i}]") for i, v in enumerate(raw)]


def _unit_convert(spec: dict) -> tuple[float, dict]:
    quantity = str(spec.get("quantity", "") or "").strip().lower()
    table = _UNITS.get(quantity)
    if table is None:
        raise ValueError(
            f"[QUANT] unit_convert: undeclared quantity {quantity!r}; "
            f"declared: {sorted(_UNITS)}")
    src = str(spec.get("from", "") or "")
    dst = str(spec.get("to", "") or "")
    if src not in table or dst not in table:
        raise ValueError(
            f"[QUANT] unit_convert: units {src!r}->{dst!r} not declared for "
            f"{quantity!r}; declared: {sorted(table)}")
    value = _number(spec.get("value"), "value")
    return value * table[src] / table[dst], {"quantity": quantity,
                                             "from": src, "to": dst}


def _apply(op: str, spec: dict) -> tuple[float, dict]:
    if op == "sum":
        return float(sum(_values(spec))), {}
    if op == "mean":
        vals = _values(spec)
        return sum(vals) / len(vals), {"n": len(vals)}
    if op == "median":
        vals = sorted(_values(spec))
        mid = len(vals) // 2
        median = vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2
        return median, {"n": len(vals)}
    if op == "min":
        return min(_values(spec)), {}
    if op == "max":
        return max(_values(spec)), {}
    if op == "percent_change":
        old = _number(spec.get("old"), "old")
        new = _number(spec.get("new"), "new")
        if old == 0:
            raise ValueError("[QUANT] percent_change: 'old' cannot be zero")
        return (new - old) / old * 100.0, {"percent_change": "%"}
    if op == "ratio":
        num = _number(spec.get("numerator"), "numerator")
        den = _number(spec.get("denominator"), "denominator")
        if den == 0:
            raise ValueError("[QUANT] ratio: 'denominator' cannot be zero")
        return num / den, {}
    if op == "weighted_mean":
        vals = _values(spec)
        weights = _values(spec, "weights")
        if len(vals) != len(weights):
            raise ValueError(
                f"[QUANT] weighted_mean: {len(vals)} values vs "
                f"{len(weights)} weights")
        total = sum(weights)
        if total == 0:
            raise ValueError("[QUANT] weighted_mean: weights sum to zero")
        return sum(v * w for v, w in zip(vals, weights)) / total, {}
    if op == "compound_growth":
        initial = _number(spec.get("initial"), "initial")
        final = _number(spec.get("final"), "final")
        periods = _number(spec.get("periods"), "periods")
        if initial <= 0:
            raise ValueError("[QUANT] compound_growth: 'initial' must be > 0")
        if periods <= 0:
            raise ValueError("[QUANT] compound_growth: 'periods' must be > 0")
        growth = (final / initial) ** (1.0 / periods) - 1.0
        return growth * 100.0, {"compound_growth": "% per period"}
    if op == "unit_convert":
        return _unit_convert(spec)
    raise ValueError(f"[QUANT] unknown op {op!r}; expected one of {OPS}")


def compute(spec: dict, *, computed_at: str | None = None) -> dict:
    """Run one declared operation; returns a JSON-serialisable record."""
    if not isinstance(spec, dict):
        raise ValueError("[QUANT] spec must be an object")
    formula_id = spec.get("formula_id")
    if not isinstance(formula_id, str) or not formula_id.strip():
        raise ValueError("[QUANT] spec needs a non-empty 'formula_id'")
    op = spec.get("op")
    if op not in OPS:
        raise ValueError(f"[QUANT] unknown op {op!r}; expected one of {OPS}")
    sources = spec.get("source_urls", []) or []
    if not isinstance(sources, list) or not all(
            isinstance(u, str) and u.strip() for u in sources):
        raise ValueError("[QUANT] 'source_urls' must be a list of URLs")
    result, extra_units = _apply(op, spec)
    if not math.isfinite(result):
        raise ValueError("[QUANT] result is not finite; refusing NaN/Inf")
    units = dict(spec.get("units") or {})
    units.update(extra_units)
    inputs = {k: v for k, v in spec.items()
              if k not in ("formula_id", "op", "units", "assumptions",
                           "source_urls")}
    return {
        "formula_id": formula_id,
        "op": op,
        "inputs": inputs,
        "units": units,
        "assumptions": list(spec.get("assumptions") or []),
        "result": result,
        "computed_at": computed_at or _utcnow(),
        "source_urls": list(sources),
    }


def to_markdown_block(result: dict) -> str:
    """Render one computed result for the report (inputs preserved)."""
    if not isinstance(result, dict) or "formula_id" not in result:
        raise ValueError("[QUANT] to_markdown_block needs a compute() result")
    units = result.get("units") or {}
    units_s = ", ".join(f"{k}={v}" for k, v in units.items()) or "—"
    assumptions = result.get("assumptions") or []
    lines = [
        f"**{result['formula_id']}** (`{result.get('op')}`) = "
        f"**{result.get('result')}**",
        f"- Entradas: `{result.get('inputs')}`",
        f"- Unidades: {units_s}",
    ]
    if assumptions:
        lines.append("- Premissas: " + "; ".join(str(a) for a in assumptions))
    if result.get("source_urls"):
        lines.append("- Fontes dos dados: " +
                     ", ".join(result["source_urls"]))
    lines.append(f"- Calculado em: {result.get('computed_at')}")
    return "\n".join(lines)
