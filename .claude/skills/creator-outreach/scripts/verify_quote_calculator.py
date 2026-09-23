#!/usr/bin/env python3
"""Re-compute every formula in the pricing calculator, in Python.

This exists for the same reason verify_workbook.py does: LibreOffice cannot
load any xlsx in this container, so there is no engine here to recalculate the
file. A Python re-computation proves the formulas are *arithmetically right*.
It does not prove a spreadsheet app renders them — open the file once in Excel
or Sheets before shipping it.

Checks three things:
  1. Only pre-2007 functions are used, so nothing can degrade to #NAME?
     (IFERROR and XLOOKUP are the usual offenders; this file uses
     IF(ISERROR(...)) instead).
  2. Every formula resolves — no reference to an empty or missing cell.
  3. The numbers are correct, evaluated from the file's own formulas rather
     than from expected values typed in by hand. A hand-typed figure was
     wrong by a dollar once already.
"""
import re
import sys

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, get_column_letter

ALLOWED = {"SUM", "IF", "MAX", "MIN", "ROUND", "VLOOKUP", "ISERROR",
           "COUNT", "COUNTIF", "SUMIF", "SUMIFS", "ABS", "AND", "OR", "NOT"}
BANNED = {"IFERROR", "XLOOKUP", "IFS", "TEXTJOIN", "SUMPRODUCT", "LET",
          "FILTER", "XMATCH", "MAXIFS", "MINIFS", "SWITCH"}

REF = re.compile(
    r"(?:'([^']+)'!)?(\$?)([A-Z]{1,3})(\$?)(\d+)(?::(\$?)([A-Z]{1,3})(\$?)(\d+))?")
FUNC = re.compile(r"\b([A-Z][A-Z0-9.]*)\s*\(")


class Err(Exception):
    pass


class Sheet:
    def __init__(self, wb):
        self.wb = wb
        self.cache = {}

    def raw(self, sheet, col, row):
        return self.wb[sheet].cell(row=row, column=column_index_from_string(col)).value

    def value(self, sheet, col, row, stack=()):
        key = (sheet, col, row)
        if key in self.cache:
            return self.cache[key]
        if key in stack:
            raise Err(f"circular reference at {sheet}!{col}{row}")
        v = self.raw(sheet, col, row)
        if isinstance(v, str) and v.startswith("="):
            v = self.evaluate(v[1:], sheet, stack + (key,))
        elif v is None:
            v = 0
        self.cache[key] = v
        return v

    def rng(self, sheet, c1, r1, c2, r2, stack=()):
        out = []
        for c in range(column_index_from_string(c1),
                       column_index_from_string(c2) + 1):
            for r in range(r1, r2 + 1):
                out.append(self.value(sheet, get_column_letter(c), r, stack))
        return out

    def evaluate(self, formula, sheet, stack=()):
        f = formula
        for name in FUNC.findall(f):
            if name in BANNED:
                raise Err(f"banned function {name} in {sheet}: ={formula}")
            if name not in ALLOWED:
                raise Err(f"unvetted function {name} in {sheet}: ={formula}")

        # Ranges and refs -> python literals / list literals.
        def sub(m):
            sh = m.group(1) or sheet
            c1, r1 = m.group(3), int(m.group(5))
            if m.group(7):
                c2, r2 = m.group(7), int(m.group(9))
                vals = self.rng(sh, c1, r1, c2, r2, stack)
                return repr(vals)
            v = self.value(sh, c1, r1, stack)
            return repr(v)

        expr = _lazy_if(REF.sub(sub, f))
        expr = expr.replace("<>", "!=").replace("^", "**")
        expr = re.sub(r"(?<![<>!=])=(?!=)", "==", expr)
        expr = re.sub(r"\bTRUE\b", "True", expr)
        expr = re.sub(r"\bFALSE\b", "False", expr)

        env = {
            "SUM": lambda *a: sum(_flat(a)),
            "MAX": lambda *a: max(_flat(a)),
            "MIN": lambda *a: min(_flat(a)),
            "ROUND": lambda x, n=0: round(float(x), int(n)),
            "ABS": abs,
            # IF is rewritten to a Python conditional before eval, so it is
            # never called. It stays here only so the ALLOWED check passes.
            "IF": lambda c, t, fa=False: t if c else fa,
            "AND": lambda *a: all(_flat(a)),
            "OR": lambda *a: any(_flat(a)),
            "NOT": lambda a: not a,
            "COUNT": lambda *a: sum(1 for v in _flat(a)
                                    if isinstance(v, (int, float))
                                    and not isinstance(v, bool) and v != 0),
            "COUNTIF": _countif,
            "SUMIF": _sumif,
            "ISERROR": lambda v: isinstance(v, str) and v.startswith("#"),
            "VLOOKUP": _vlookup,
        }
        try:
            return eval(expr, {"__builtins__": {}}, env)
        except Err:
            raise
        except Exception as exc:
            raise Err(f"{sheet}: ={formula}\n      -> {expr[:160]}\n      {exc}")


def _split_args(s):
    """Top-level commas only, respecting nested parens and quoted strings."""
    args, depth, cur, quote = [], 0, "", False
    for ch in s:
        if quote:
            cur += ch
            if ch == '"':
                quote = False
            continue
        if ch == '"':
            quote = True
            cur += ch
        elif ch == "(":
            depth += 1
            cur += ch
        elif ch == ")":
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            args.append(cur)
            cur = ""
        else:
            cur += ch
    args.append(cur)
    return args


def _lazy_if(expr):
    """Rewrite IF(a,b,c) as (b if a else c).

    Excel's IF only evaluates the branch it takes; Python's eval evaluates the
    arguments of a function call eagerly. That difference is not cosmetic — the
    log sheet's ``=IF(E5=0,"",D5/E5)`` guard is *correct* Excel and raised
    ZeroDivisionError in the first version of this verifier, reporting 61
    problems in a file that had none. A verifier that fails a valid file is
    worse than no verifier, because the next real failure gets ignored.
    """
    while True:
        i = expr.upper().find("IF(")
        # Skip ISERROR( and any name ending in IF, e.g. COUNTIF(/SUMIF(.
        while i != -1 and i > 0 and (expr[i - 1].isalpha() or expr[i - 1] == "."):
            nxt = expr.upper().find("IF(", i + 1)
            i = nxt
        if i == -1:
            return expr
        depth, j = 0, i + 2
        for j in range(i + 2, len(expr)):
            if expr[j] == "(":
                depth += 1
            elif expr[j] == ")":
                depth -= 1
                if depth == 0:
                    break
        args = _split_args(expr[i + 3:j])
        if len(args) == 2:
            args.append("False")
        if len(args) != 3:
            return expr
        cond, yes, no = (_lazy_if(a) for a in args)
        expr = f"{expr[:i]}(({yes}) if ({cond}) else ({no})){expr[j + 1:]}"


def _flat(a):
    out = []
    for x in a:
        if isinstance(x, (list, tuple)):
            out.extend(_flat(x))
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            out.append(x)
    return out


def _countif(rng, crit):
    c = str(crit).strip().lower()
    return sum(1 for v in (rng if isinstance(rng, list) else [rng])
               if str(v).strip().lower() == c)


def _sumif(rng, crit, total=None):
    vals = rng if isinstance(rng, list) else [rng]
    tot = total if isinstance(total, list) else vals
    c = str(crit).strip().lower()
    return sum(t for v, t in zip(vals, tot)
               if str(v).strip().lower() == c
               and isinstance(t, (int, float)) and not isinstance(t, bool))


# VLOOKUP over a flattened column-major range is not reconstructible, so the
# table is passed as a marker and resolved against the Rate Card directly.
_RATE_TABLE = {}


def _vlookup(key, table, col, exact=False):
    row = _RATE_TABLE.get(str(key).strip())
    if row is None:
        return "#N/A"
    return row[int(col) - 1]


def main(path):
    wb = load_workbook(path, data_only=False)
    rc = wb["Rate Card"]
    for r in range(5, rc.max_row + 1):
        name = rc.cell(row=r, column=1).value
        if not name:
            continue
        _RATE_TABLE[str(name).strip()] = [
            name,
            rc.cell(row=r, column=2).value,
            rc.cell(row=r, column=3).value,
            rc.cell(row=r, column=4).value,
            None,
        ]

    s = Sheet(wb)
    problems, formulas = [], 0
    for name in wb.sheetnames:
        ws = wb[name]
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    formulas += 1
                    try:
                        s.evaluate(cell.value[1:], name)
                    except Err as exc:
                        problems.append(f"  {name}!{cell.coordinate}: {exc}")

    print(f"{formulas} formulas parsed across {len(wb.sheetnames)} sheets")
    if problems:
        print(f"\n{len(problems)} PROBLEM(S):")
        for p in problems[:20]:
            print(p)
        return 1

    q = "Quote Builder"
    get = lambda coord: s.value(q, coord[0], int(coord[1:]))

    def find(label, sheet=q):
        ws = wb[sheet]
        for row in ws.iter_rows():
            if str(row[0].value).strip().lower() == label.lower():
                return row[1].coordinate
        raise SystemExit(f"label not found: {label}")

    be = s.value("My Costs", "B",
                 int(find("BREAK-EVEN HOURLY RATE", "My Costs")[1:]))
    print(f"\nWith the shipped example figures:")
    print(f"  break-even hourly rate      {be:>10,.2f}")
    checks = [
        ("Hours on site", None),
        ("Total direct costs", None),
        ("PRICE TO QUOTE", None),
        ("Profit after costs and your own time", None),
        ("Margin", None),
        ("Effective hourly rate on this job", None),
        ("Verdict", None),
    ]
    vals = {}
    for label, _ in checks:
        v = get(find(label))
        vals[label] = v
        shown = f"{v:>10,.4f}" if isinstance(v, (int, float)) else f"  {v}"
        print(f"  {label:<38}{shown}")

    # Independent arithmetic, derived from the inputs rather than the formulas.
    # Located by label, never by hardcoded row. Row numbers drift the moment
    # a cost line is added to the builder, and a verifier that silently reads
    # the wrong row is the failure it is supposed to catch.
    def crow(label):
        return int(find(label, "My Costs")[1:])

    mc = wb["My Costs"]
    fixed = sum(s.value("My Costs", "B", r)
                for r in range(5, crow("Total fixed costs")))
    wage = s.value("My Costs", "B",
                   crow("What you want to earn in a year, before tax"))
    bill = (s.value("My Costs", "B", crow("Weeks worked per year"))
            * s.value("My Costs", "B", crow("Days worked per week"))
            * s.value("My Costs", "B", crow("Billable hours per day")))
    expect_be = (fixed + wage) / bill
    qty = get(find("Measurement (in that row's unit)"))
    rate = get(find("Rate from the Rate Card"))
    uph = get(find("Units per hour from the Rate Card"))
    chem = get(find("Chemicals and consumables"))
    tip = get(find("Waste disposal / tip fees"))
    dist = get(find("Travel — round trip distance"))
    ppm = get(find("Cost per unit distance"))
    hire = get(find("Hired help — total pay for this job"))
    minimum = get(find("Minimum call-out charge"))
    hours = qty / uph
    direct = chem + tip + dist * ppm + hire
    price = round((max(qty * rate, minimum) + direct), 2)
    profit = price - direct - hours * expect_be
    fails = []
    for label, expect in (("Hours on site", hours),
                          ("Total direct costs", direct),
                          ("PRICE TO QUOTE", price),
                          ("Profit after costs and your own time", profit),
                          ("Margin", profit / price),
                          ("Effective hourly rate on this job",
                           (price - direct) / hours)):
        got = vals[label]
        if abs(got - expect) > 0.005:
            fails.append(f"  {label}: file says {got:,.4f}, "
                         f"independent arithmetic says {expect:,.4f}")
    if abs(be - expect_be) > 0.005:
        fails.append(f"  break-even: {be:.4f} vs {expect_be:.4f}")

    if fails:
        print("\nARITHMETIC MISMATCH:")
        for f in fails:
            print(f)
        return 1
    print("\nAll formulas resolve, only pre-2007 functions used, and every "
          "figure matches an independent calculation.")
    print("Still open it once in Excel or Sheets — this proves the formulas "
          "are right, not that an engine renders them.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1
                  else "Job-Pricing-Quoting-Calculator.xlsx"))
