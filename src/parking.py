"""
Parking generator — isi Template Parkir MDT dari file CAS Activities.
Dipanggil via: rpa parking
"""
import datetime as dt
import os
import random
import sys

import openpyxl
from openpyxl.cell.cell import MergedCell

# ── KONFIGURASI TEMPLATE ─────────────────────────────────────────────────────
SHEET_NAME = "Sheet1"

SLOT_ROWS = (4, 28, 52, 70, 94, 118, 136, 160, 184, 202)
SLOTS = [(col, row) for row in SLOT_ROWS for col in ("C", "M")]
LEFT_COLS, RIGHT_COLS = (1, 10), (11, 20)
BLOCK_UP, BLOCK_DOWN = 3, 14

# ── KONFIGURASI CAS ──────────────────────────────────────────────────────────
ROLE_COL, DATE_COL, START_COL, STOP_COL = 5, 8, 9, 10
ROLE_VALUE = "Account Support"

# ── ATURAN SHIFT MALAM ───────────────────────────────────────────────────────
NIGHT_EARLY = dt.time(22, 59)
NIGHT_LATE  = dt.time(0, 0)
NIGHT_START = dt.time(23, 0)

# ── JITTER ───────────────────────────────────────────────────────────────────
IN_MINUTE_RANGE = (10, 23)
OUT_EXTRA_MIN   = (120, 179)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _to_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    return dt.datetime.strptime(str(v).strip(), "%Y-%m-%d").date()


def _to_time(v):
    if isinstance(v, dt.datetime):
        return v.time().replace(second=0, microsecond=0)
    if isinstance(v, dt.time):
        return v.replace(second=0, microsecond=0)
    return dt.datetime.strptime(str(v).strip()[:5], "%H:%M").time()


def read_cas(path: str) -> list:
    ws = openpyxl.load_workbook(path, data_only=True).active
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if r[ROLE_COL - 1] != ROLE_VALUE:
            continue
        rows.append((
            _to_date(r[DATE_COL - 1]),
            _to_time(r[START_COL - 1]),
            _to_time(r[STOP_COL - 1]),
        ))
    return rows


def build_entries(rows: list) -> list:
    """Gabungkan shift malam, hasilkan list (masuk, keluar) terurut."""
    used, entries = set(), []
    for i, (d, s, _e) in enumerate(rows):
        if s != NIGHT_EARLY:
            continue
        nxt = d + dt.timedelta(days=1)
        for j, (d2, s2, e2) in enumerate(rows):
            if j not in used and d2 == nxt and s2 == NIGHT_LATE:
                used.update((i, j))
                entries.append((
                    dt.datetime.combine(d, NIGHT_START),
                    dt.datetime.combine(d2, e2),
                ))
                break
    for i, (d, s, e) in enumerate(rows):
        if i not in used:
            entries.append((dt.datetime.combine(d, s), dt.datetime.combine(d, e)))
    entries.sort()
    return entries


def apply_jitter(entries: list) -> list:
    result = []
    for masuk, keluar in entries:
        m = (masuk - dt.timedelta(hours=1)).replace(
            minute=random.randint(*IN_MINUTE_RANGE),
            second=random.randint(0, 59),
        )
        k = keluar + dt.timedelta(
            minutes=random.randint(*OUT_EXTRA_MIN),
            seconds=random.randint(0, 59),
        )
        result.append((m, k))
    return result


def clear_block(ws, row: int, cols: tuple):
    for r in range(row - BLOCK_UP, row + BLOCK_DOWN + 1):
        for c in range(cols[0], cols[1] + 1):
            cell = ws.cell(r, c)
            if not isinstance(cell, MergedCell):
                cell.value = None


def write_template(template_path: str, entries: list, out_path: str):
    """Isi template dengan entries dan simpan ke out_path."""
    wb = openpyxl.load_workbook(template_path)
    ws = wb[SHEET_NAME]

    for (col, row), (masuk, keluar) in zip(SLOTS, entries):
        ws[f"{col}{row}"]     = masuk
        ws[f"{col}{row + 1}"] = keluar

    for col, row in SLOTS[len(entries):]:
        clear_block(ws, row, LEFT_COLS if col == "C" else RIGHT_COLS)

    wb.calculation.fullCalcOnLoad = True
    wb.save(out_path)


def default_output_name(cas_path: str, parking_dir: str) -> str:
    """Buat nama output otomatis di parking_dir dari nama file CAS."""
    base = os.path.splitext(os.path.basename(cas_path))[0]
    for prefix in ("CAS_Activities_", "CAS Activities ", "CAS_Activity_"):
        if base.startswith(prefix):
            base = base[len(prefix):]
            break
    return os.path.join(parking_dir, f"MDT PARKIR {base}.xlsx")
