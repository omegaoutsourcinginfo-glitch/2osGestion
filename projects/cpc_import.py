"""
CPC Excel import helper.

Finds the row:
  IV- Total Charge de Production (III1+III2+III3+III4+III5+III6)+II
and returns its MONTANT TOTAL as Total investissement (DH).

Used by:
  - project form tab « CPC / Investissement »
  - Planning financier admin
  - AJAX preview endpoint /projets/cpc/preview-total/
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import BinaryIO

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

# Match the CPC label for the investment total row (column B in the template).
IV_LABEL = re.compile(
    r"IV\s*[-–]?\s*Total\s+Charge\s+de\s+Production",
    re.IGNORECASE,
)
# Match the "MONTANT TOTAL" header to locate the amount column (usually N).
MONTANT_HEADER = re.compile(r"MONTANT", re.IGNORECASE)
CELL_REF = re.compile(r"\$?([A-Za-z]{1,3})\$?(\d+)")
RANGE_REF = re.compile(
    r"\$?([A-Za-z]{1,3})\$?(\d+)\s*:\s*\$?([A-Za-z]{1,3})\$?(\d+)"
)


class CpcImportError(ValueError):
    """Raised when the CPC Excel file cannot yield Total investissement."""


def extract_total_investissement(file_obj: BinaryIO | bytes) -> Decimal:
    """
    Read a CPC .xlsx and return IV = (III1+…+III6)+II from MONTANT TOTAL.

    Formula cells are evaluated recursively (SUM, +, *, %, cell refs).
    If the IV cell is a plain number, that value is used instead.
    """
    raw = file_obj if isinstance(file_obj, (bytes, bytearray)) else file_obj.read()
    if hasattr(file_obj, "seek"):
        try:
            file_obj.seek(0)
        except Exception:
            pass

    wb_values = load_workbook(BytesIO(raw), data_only=True, read_only=True)
    wb_formulas = load_workbook(BytesIO(raw), data_only=False, read_only=False)

    last_error: Exception | None = None
    try:
        for sheet_name in wb_formulas.sheetnames:
            ws_f = wb_formulas[sheet_name]
            ws_v = wb_values[sheet_name] if sheet_name in wb_values.sheetnames else None
            try:
                total = _extract_from_sheet(ws_f, ws_v)
            except CpcImportError as exc:
                last_error = exc
                continue
            if total is not None:
                return total.quantize(Decimal("0.01"))
    finally:
        wb_values.close()
        wb_formulas.close()

    if last_error is not None:
        raise last_error
    raise CpcImportError(
        "Ligne « IV- Total Charge de Production » introuvable dans le fichier Excel."
    )


def _extract_from_sheet(
    ws_formulas: Worksheet,
    ws_values: Worksheet | None,
) -> Decimal | None:
    iv_row, montant_col = _find_iv_cell(ws_formulas)
    if iv_row is None or montant_col is None:
        return None

    formula_cell = ws_formulas.cell(iv_row, montant_col).value
    if isinstance(formula_cell, str) and formula_cell.startswith("="):
        return _resolve_cell(ws_formulas, iv_row, montant_col, {}, set())

    direct = _to_decimal(formula_cell)
    if direct is not None:
        return direct

    if ws_values is not None:
        cached = _to_decimal(ws_values.cell(iv_row, montant_col).value)
        if cached is not None:
            return cached

    raise CpcImportError(
        "Montant Total investissement (colonne MONTANT TOTAL) vide ou non calculable."
    )


def _find_iv_cell(ws: Worksheet) -> tuple[int | None, int | None]:
    montant_col = _find_montant_column(ws)
    iv_row = None
    for row in ws.iter_rows(
        min_row=1,
        max_row=ws.max_row or 1,
        max_col=min(8, ws.max_column or 1),
    ):
        for cell in row:
            if isinstance(cell.value, str) and IV_LABEL.search(cell.value):
                iv_row = cell.row
                break
        if iv_row is not None:
            break
    if iv_row is None:
        return None, None
    if montant_col is None:
        # Default CPC layout: MONTANT TOTAL in column N.
        montant_col = 14
    return iv_row, montant_col


def _find_montant_column(ws: Worksheet) -> int | None:
    max_row = min(30, ws.max_row or 1)
    max_col = ws.max_column or 1
    for row in ws.iter_rows(min_row=1, max_row=max_row, max_col=max_col):
        for cell in row:
            if isinstance(cell.value, str) and MONTANT_HEADER.search(cell.value):
                return cell.column
    return None


def _resolve_cell(
    ws: Worksheet,
    row: int,
    col: int,
    cache: dict[str, Decimal],
    visiting: set[str],
) -> Decimal:
    key = f"{get_column_letter(col)}{row}"
    if key in cache:
        return cache[key]
    if key in visiting:
        return Decimal("0")

    visiting.add(key)
    value = ws.cell(row, col).value
    if value is None or value == "":
        result = Decimal("0")
    elif isinstance(value, str) and value.startswith("="):
        result = _eval_formula(ws, value[1:], cache, visiting)
    else:
        parsed = _to_decimal(value)
        result = parsed if parsed is not None else Decimal("0")
    visiting.remove(key)
    cache[key] = result
    return result


def _eval_formula(
    ws: Worksheet,
    formula: str,
    cache: dict[str, Decimal],
    visiting: set[str],
) -> Decimal:
    expr = formula.strip()
    if expr.startswith("+"):
        expr = expr[1:]

    sum_match = re.fullmatch(r"SUM\((.+)\)", expr, flags=re.IGNORECASE)
    if sum_match:
        total = Decimal("0")
        for part in _split_args(sum_match.group(1)):
            total += _eval_formula(ws, part, cache, visiting)
        return total

    def replace_range(match: re.Match[str]) -> str:
        c1, r1, c2, r2 = match.groups()
        cells = []
        for r in range(int(r1), int(r2) + 1):
            for c in range(
                column_index_from_string(c1),
                column_index_from_string(c2) + 1,
            ):
                cells.append(get_column_letter(c) + str(r))
        return "(" + "+".join(cells) + ")" if cells else "0"

    expr = RANGE_REF.sub(replace_range, expr)
    expr = re.sub(
        r"(?<![A-Za-z])(\d+(?:[.,]\d+)?)\s*%",
        lambda m: str(_to_decimal(m.group(1) + "%") or Decimal("0")),
        expr,
    )

    def replace_cell(match: re.Match[str]) -> str:
        col = column_index_from_string(match.group(1))
        row = int(match.group(2))
        return str(_resolve_cell(ws, row, col, cache, visiting))

    expr = CELL_REF.sub(replace_cell, expr)
    expr = expr.replace(",", ".")
    expr = re.sub(r"[^0-9+\-*/().\s]", "", expr)
    if not expr.strip():
        return Decimal("0")
    try:
        return Decimal(str(eval(expr, {"__builtins__": {}}, {})))  # noqa: S307
    except Exception as exc:
        raise CpcImportError(f"Formule CPC non supportée: {formula}") from exc


def _split_args(args: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in args:
        if ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return [p for p in parts if p]


def _to_decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        text = value.strip()
        if not text or text.startswith("="):
            return None
        percent = text.endswith("%")
        if percent:
            text = text[:-1].strip()
        text = text.replace("\u00a0", " ").replace(" ", "").replace(",", ".")
        try:
            number = Decimal(text)
        except InvalidOperation:
            return None
        if percent:
            number = number / Decimal("100")
        return number
    return None
