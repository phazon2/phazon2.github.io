#!/usr/bin/env python3
"""Verify the workbook's formulas without a spreadsheet engine.

LibreOffice cannot load any xlsx in this container ("source file could not be
loaded" on a three-cell file), so the usual recalc check is unavailable. This is
not a substitute for it and does not pretend to be: it cannot prove Excel will
render a value. What it does prove is the part that actually goes wrong by hand —
that each formula references the columns and criteria cells it was meant to, and
that the arithmetic it describes produces the right number for the example rows.

Three checks:
  1. FUNCTIONS   every function used is pre-2007 (SUMIFS, SUM, MONTH, IF) and so
                 needs no _xlfn. prefix and cannot become #NAME?.
  2. REFERENCES  each SUMIFS points at Transactions F (amount), B (month) and
                 D (category), and at a month-number cell in row 5.
  3. ARITHMETIC  SUMIFS re-implemented in Python over the example rows; the value
                 each cell should display is computed and compared against an
                 independent expectation built straight from the example data.
"""

import re
import sys
from collections import defaultdict

import openpyxl

SAFE = {"SUMIFS", "SUM", "MONTH", "IF", "IFERROR", "INDEX", "MATCH", "SUMPRODUCT"}
BANNED = {"XLOOKUP", "XMATCH", "SORT", "FILTER", "UNIQUE", "SEQUENCE", "TEXTJOIN",
          "CONCAT", "IFS", "SWITCH", "MAXIFS", "MINIFS"}

PATH = "12-Month-Bookkeeping-Workbook-SAMPLE.xlsx"
fail = []


def check_functions(wb):
    used = defaultdict(int)
    for ws in wb:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("="):
                    for fn in re.findall(r"([A-Z][A-Z0-9_.]*)\s*\(", c.value.upper()):
                        used[fn.replace("_XLFN.", "")] += 1
    print("  functions used:", ", ".join(f"{k}×{v}" for k, v in sorted(used.items())))
    for fn in used:
        if fn in BANNED:
            fail.append(f"banned function {fn} — LibreOffice/openpyxl cannot render it")
        elif fn not in SAFE:
            fail.append(f"unreviewed function {fn}")
    return used


def check_references(wb):
    pnl = wb["Monthly P&L"]
    checked = 0
    for row in pnl.iter_rows(min_row=8, max_row=40, min_col=2, max_col=13):
        for c in row:
            if not (isinstance(c.value, str) and c.value.startswith("=SUMIFS")):
                continue
            f = c.value
            if "Transactions!$F$" not in f:
                fail.append(f"{c.coordinate}: sum range is not Transactions!F (amount)")
            if "Transactions!$B$" not in f:
                fail.append(f"{c.coordinate}: month criteria range is not Transactions!B")
            if "Transactions!$D$" not in f:
                fail.append(f"{c.coordinate}: category criteria range is not Transactions!D")
            if not re.search(r",[A-Z]{1,2}\$5,", f):
                fail.append(f"{c.coordinate}: month criterion does not point at row 5")
            if f"$A{c.row}" not in f:
                fail.append(f"{c.coordinate}: category criterion is not $A{c.row}")
            checked += 1
    print(f"  SUMIFS reference shape verified on {checked} cells")

    # the month-number header row must read 1..12 under Jan..Dec
    nums = [pnl.cell(5, 2 + i).value for i in range(12)]
    if nums != list(range(1, 13)):
        fail.append(f"month-number row 5 is {nums}, expected 1..12")
    else:
        print("  month-number row reads 1..12 under Jan..Dec")


def sumifs(rows, month, category):
    """The Python twin of the SUMIFS in each P&L cell."""
    return sum(amt for (m, cat, amt) in rows if m == month and cat == category)


def check_arithmetic(wb):
    tx = wb["Transactions"]
    rows = []
    for r in range(5, 400):
        d = tx.cell(r, 1).value
        cat = tx.cell(r, 4).value
        amt = tx.cell(r, 6).value
        if d is None or amt is None:
            continue
        # column B is =MONTH($A{r}); evaluate it the way the sheet will
        rows.append((d.month, cat, float(amt)))
    print(f"  {len(rows)} example rows read from Transactions")

    # Independent expectation, written from the example data by hand.
    expected = {
        (1, "Sales - Products"): 1240.50,
        (1, "Software"): 119.00,
        (1, "Supplies - Materials"): 214.86,
        (2, "Sales - Services"): 450.00,
        (2, "Bank & Merchant Fees"): 38.42,
        (3, "Rent or Lease"): 600.00,
        (4, "Sales - Products"): 0.0,      # nothing in April
        (1, "Sales - Services"): 0.0,      # services started in Feb
    }
    for (month, cat), want in expected.items():
        got = sumifs(rows, month, cat)
        ok = abs(got - want) < 0.005
        print(f"    month {month:>2} · {cat:<22} formula yields {got:>9.2f} "
              f"expected {want:>9.2f}  {'ok' if ok else 'MISMATCH'}")
        if not ok:
            fail.append(f"SUMIFS logic wrong for month {month} / {cat}: {got} != {want}")

    # Net profit identity: income minus expenses, per month and for the year.
    inc = sum(a for (m, c, a) in rows if c in
              ("Sales - Products", "Sales - Services", "Other Income"))
    exp = sum(a for (m, c, a) in rows if c not in
              ("Sales - Products", "Sales - Services", "Other Income"))
    print(f"  year totals from examples: income {inc:,.2f} · expenses {exp:,.2f} "
          f"· net {inc - exp:,.2f}")
    if round(inc, 2) != 1690.50 or round(exp, 2) != 972.28:
        fail.append(f"example totals moved: income {inc}, expenses {exp}")


def check_tax(wb):
    ws = wb["Sales Tax"]
    rate = ws["B4"].value
    cat = ws["B5"].value
    if not isinstance(rate, float):
        fail.append("Sales Tax B4 rate is not a number")
    if cat not in ("Sales - Products", "Sales - Services", "Other Income"):
        fail.append(f"Sales Tax B5 '{cat}' is not one of the income categories")
    # Jan taxable sales 1240.50 at 7.25% = 89.94
    want = round(1240.50 * rate, 2)
    print(f"  sales tax: rate {rate:.2%} on '{cat}' -> January tax {want:.2f}")
    running = ws["D8"].value
    if running != "=C8":
        fail.append(f"running total should start at =C8, found {running}")


def main():
    wb = openpyxl.load_workbook(PATH)
    print("sheets:", ", ".join(wb.sheetnames))
    print("\n1. FUNCTIONS")
    check_functions(wb)
    print("\n2. REFERENCES")
    check_references(wb)
    print("\n3. ARITHMETIC")
    check_arithmetic(wb)
    print("\n4. SALES TAX")
    check_tax(wb)

    print()
    if fail:
        print(f"{len(fail)} PROBLEM(S):")
        for f in fail:
            print("  -", f)
        sys.exit(1)
    print("all checks passed — formula references and arithmetic verified.")
    print("NOT verified: that a spreadsheet engine renders them (LibreOffice "
          "cannot open any xlsx in this container).")


if __name__ == "__main__":
    main()
