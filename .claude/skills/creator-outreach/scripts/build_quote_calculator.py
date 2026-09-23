#!/usr/bin/env python3
"""Build the Job Pricing & Quoting Calculator.

Built from a demand cluster that appeared in four unrelated channels across two
niches — exterior cleaning, lawn care and acrylic crafts — all asking the same
question in their own words:

    "How do you even start to price a job of that size"
    "How do you work out the pricing of a roof cleaning or patio cleaning job"
    "how much do you charge per meter sid ?"
    "Can you go over how you price jobs like this one?"
    "How do you price your acrylic products and calculate profit margins?"

Those are verbatim, verified against the harvests. The design follows what they
actually asked for, not what is easy to build:

* Per-unit rates by surface (Partridge's audience quotes per square metre).
* A day rate for machine work (the lawn-care audience quotes per day/acre).
* Risk multipliers, because one of them asked the hard version: "How do you
  quote when you don't completely know what you are cleaning?"
* A break-even hourly rate, which nobody asked for and is the thing that makes
  the rest mean anything — a quote is only good news relative to your costs.

Unit- and currency-agnostic on purpose: one asked per metre in pounds, another
per acre in dollars.

Formulas are pre-2007 only (no IFERROR, no XLOOKUP) so the file cannot degrade
to #NAME? in Google Sheets or older Excel. verify_quote_calculator.py
re-computes every one in Python.
"""
import argparse

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

INK = "1B1F22"
DARK = "12342F"
MID = "1E7A6B"
LIGHT = "F1F5F5"
ACCENT = "7FD1C1"

H1 = Font(name="Calibri", size=16, bold=True, color=DARK)
NOTE = Font(name="Calibri", size=10, italic=True, color="6B7A7D")
HEAD = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
BODY = Font(name="Calibri", size=11, color=INK)
BOLD = Font(name="Calibri", size=11, bold=True, color=INK)
BIG = Font(name="Calibri", size=14, bold=True, color="FFFFFF")

FILL_HEAD = PatternFill("solid", fgColor=DARK)
FILL_ACC = PatternFill("solid", fgColor=MID)
FILL_BAND = PatternFill("solid", fgColor=LIGHT)
FILL_IN = PatternFill("solid", fgColor="FFF8DC")

THIN = Side(style="thin", color="D5DBDC")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _title(ws, text, sub, width):
    ws["A1"] = text
    ws["A1"].font = H1
    ws["A2"] = sub
    ws["A2"].font = NOTE
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=width)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=width)
    ws.sheet_view.showGridLines = False


def _header(ws, row, labels, widths=None):
    for i, lab in enumerate(labels, start=1):
        c = ws.cell(row=row, column=i, value=lab)
        c.font = HEAD
        c.fill = FILL_HEAD
        c.border = BOX
        c.alignment = Alignment(horizontal="center", vertical="center",
                                wrap_text=True)
    if widths:
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[row].height = 28


def _input(ws, cell, value, fmt=None):
    c = ws[cell]
    c.value = value
    c.font = BODY
    c.fill = FILL_IN
    c.border = BOX
    if fmt:
        c.number_format = fmt
    return c


# --------------------------------------------------------------------------
# 1. Start here
# --------------------------------------------------------------------------
def sheet_start(wb):
    ws = wb.create_sheet("Start here")
    _title(ws, "Job Pricing & Quoting Calculator",
           "Work through the tabs in order. Only the cream-coloured cells "
           "are for typing in.", 6)
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 96

    steps = [
        ("1. My Costs",
         "Enter what the business costs you to run for a year and how many "
         "hours you can actually bill. This gives your break-even hourly "
         "rate — the number every quote has to beat."),
        ("2. Rate Card",
         "Set your price per unit for each kind of work you do. Works in "
         "square metres, square feet, acres or per-item — you choose the "
         "unit, the sheet does not assume one."),
        ("3. Quote Builder",
         "Price one job. Enter the measurement, pick the surface, set the "
         "access and condition multipliers, add consumables and disposal. "
         "It returns the price, the hours, and the margin after your costs."),
        ("4. Quote Log",
         "Keep every quote you send, whether it was won or lost. After "
         "twenty jobs this tells you which work is actually worth doing."),
    ]
    r = 4
    for name, text in steps:
        c = ws.cell(row=r, column=2, value=name)
        c.font = Font(name="Calibri", size=12, bold=True, color=DARK)
        r += 1
        c = ws.cell(row=r, column=2, value=text)
        c.font = BODY
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 46
        r += 2

    c = ws.cell(row=r, column=2,
                value="Two things worth knowing before you quote anything")
    c.font = Font(name="Calibri", size=12, bold=True, color=DARK)
    r += 1
    for text in (
        "A price is not a profit. A job can be the biggest number you have "
        "ever quoted and still lose money once travel, consumables, "
        "disposal and your own unpaid hours are counted. That is what the "
        "margin column on the Quote Builder is for.",
        "When you cannot see the whole job, price the uncertainty, do not "
        "absorb it. The Condition and Access multipliers exist for exactly "
        "this — a roof you have not been on yet is not the same job as one "
        "you have. Quote the range, or quote the risk.",
    ):
        c = ws.cell(row=r, column=2, value="• " + text)
        c.font = BODY
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = 46
        r += 1

    ws.cell(row=r + 1, column=2,
            value="No macros. Opens in Excel, Google Sheets, Numbers and "
                  "LibreOffice.").font = NOTE
    return ws


# --------------------------------------------------------------------------
# 2. My Costs  -> break-even hourly rate
# --------------------------------------------------------------------------
COSTS = [
    ("Vehicle — payments, fuel, insurance, upkeep", 7200),
    ("Equipment — payments, repairs, replacement fund", 3600),
    ("Business insurance and licences", 1400),
    ("Phone, internet, software, bookkeeping", 900),
    ("Advertising and website", 1200),
    ("Premises or storage", 0),
    ("Accountant and bank charges", 600),
    ("Other fixed costs", 0),
]


def sheet_costs(wb, cur):
    ws = wb.create_sheet("My Costs")
    _title(ws, "My Costs",
           "What the business costs for a year, and how many hours you can "
           "really bill. Everything else depends on this.", 4)
    _header(ws, 4, ["Fixed cost (per year)", "Amount", "", ""],
            [52, 16, 3, 40])

    r = 5
    for label, amt in COSTS:
        ws.cell(row=r, column=1, value=label).font = BODY
        ws.cell(row=r, column=1).border = BOX
        _input(ws, f"B{r}", amt, f'"{cur}"#,##0')
        r += 1

    first, last = 5, r - 1
    ws.cell(row=r, column=1, value="Total fixed costs").font = BOLD
    ws.cell(row=r, column=1).fill = FILL_BAND
    ws.cell(row=r, column=1).border = BOX
    tot = ws.cell(row=r, column=2, value=f"=SUM(B{first}:B{last})")
    tot.font = BOLD
    tot.fill = FILL_BAND
    tot.border = BOX
    tot.number_format = f'"{cur}"#,##0'
    total_row = r

    r += 2
    ws.cell(row=r, column=1, value="Your own pay").font = Font(
        name="Calibri", size=12, bold=True, color=DARK)
    r += 1
    ws.cell(row=r, column=1,
            value="What you want to earn in a year, before tax").font = BODY
    ws.cell(row=r, column=1).border = BOX
    _input(ws, f"B{r}", 32000, f'"{cur}"#,##0')
    wage_row = r

    r += 2
    ws.cell(row=r, column=1, value="Billable hours").font = Font(
        name="Calibri", size=12, bold=True, color=DARK)
    ws.cell(row=r, column=4,
            value="Be honest here. Quoting, travel, invoicing and "
                  "maintenance are not billable, and they are most of a "
                  "week.").font = NOTE
    ws.cell(row=r, column=4).alignment = Alignment(wrap_text=True,
                                                   vertical="top")
    ws.row_dimensions[r].height = 42
    r += 1
    for label, val in (("Weeks worked per year", 46),
                       ("Days worked per week", 5),
                       ("Billable hours per day", 5)):
        ws.cell(row=r, column=1, value=label).font = BODY
        ws.cell(row=r, column=1).border = BOX
        _input(ws, f"B{r}", val, "0.0")
        r += 1
    weeks, days, hours = r - 3, r - 2, r - 1

    ws.cell(row=r, column=1, value="Billable hours per year").font = BOLD
    ws.cell(row=r, column=1).fill = FILL_BAND
    ws.cell(row=r, column=1).border = BOX
    bh = ws.cell(row=r, column=2, value=f"=B{weeks}*B{days}*B{hours}")
    bh.font = BOLD
    bh.fill = FILL_BAND
    bh.border = BOX
    bh.number_format = "#,##0"
    bh_row = r

    r += 2
    ws.cell(row=r, column=1,
            value="BREAK-EVEN HOURLY RATE").font = BIG
    ws.cell(row=r, column=1).fill = FILL_ACC
    ws.cell(row=r, column=1).border = BOX
    be = ws.cell(row=r, column=2,
                 value=f"=IF(B{bh_row}=0,0,(B{total_row}+B{wage_row})/B{bh_row})")
    be.font = BIG
    be.fill = FILL_ACC
    be.border = BOX
    be.number_format = f'"{cur}"#,##0.00'
    ws.row_dimensions[r].height = 24
    ws.cell(row=r, column=4,
            value="Every hour you work has to bring in at least this much "
                  "before the business has made a penny. Quote below it and "
                  "you are paying for the privilege of working.").font = NOTE
    ws.cell(row=r, column=4).alignment = Alignment(wrap_text=True,
                                                   vertical="top")
    ws.row_dimensions[r].height = 56
    ws.breakeven = f"'My Costs'!$B${r}"
    return ws


# --------------------------------------------------------------------------
# 3. Rate Card
# --------------------------------------------------------------------------
RATES = [
    ("Block paving / driveway", "sq m", 3.50, 22),
    ("Patio — slabs", "sq m", 3.00, 25),
    ("Patio — sandstone (soft)", "sq m", 4.25, 18),
    ("Tarmac / asphalt", "sq m", 2.25, 30),
    ("Concrete", "sq m", 2.40, 28),
    ("Decking — clean only", "sq m", 4.00, 20),
    ("Roof — tile, soft wash", "sq m", 11.00, 9),
    ("Roof — moss removal by hand", "sq m", 18.00, 5),
    ("Render / wall — soft wash", "sq m", 6.50, 14),
    ("Gutter clearing", "per m run", 3.00, 30),
    ("Fascia and soffit", "per m run", 4.50, 18),
    ("Windows — domestic", "per window", 2.50, 40),
    ("Mowing — maintained lawn", "per visit", 35.00, 1),
    ("Mowing — overgrown, first cut", "per hour", 55.00, 1),
    ("Brush cutting / bush-hogging", "per acre", 180.00, 0.7),
    ("Leaf clearance", "per hour", 45.00, 1),
    ("Machine day rate — operator included", "per day", 480.00, 0.125),
]


def sheet_rates(wb, cur):
    ws = wb.create_sheet("Rate Card")
    _title(ws, "Rate Card",
           "Your price per unit, and how much of it you get through in an "
           "hour. Change the rows to match the work you actually do.", 5)
    _header(ws, 4, ["Type of work", "Unit", f"Rate ({cur} per unit)",
                    "Units done per hour", "Effective hourly rate"],
            [36, 14, 18, 18, 20])

    r = 5
    for name, unit, rate, per_hour in RATES:
        ws.cell(row=r, column=1, value=name).font = BODY
        ws.cell(row=r, column=1).border = BOX
        ws.cell(row=r, column=2, value=unit).font = BODY
        ws.cell(row=r, column=2).border = BOX
        _input(ws, f"C{r}", rate, f'"{cur}"#,##0.00')
        _input(ws, f"D{r}", per_hour, "#,##0.00")
        e = ws.cell(row=r, column=5, value=f"=C{r}*D{r}")
        e.font = BOLD
        e.border = BOX
        e.number_format = f'"{cur}"#,##0.00'
        r += 1

    last = r - 1
    ws.cell(row=r + 1, column=1,
            value="The last column is the one to argue with. If a rate's "
                  "effective hourly is under your break-even on the My Costs "
                  "tab, that line of work loses money at any volume.").font = NOTE
    ws.cell(row=r + 1, column=1).alignment = Alignment(wrap_text=True,
                                                       vertical="top")
    ws.merge_cells(start_row=r + 1, start_column=1, end_row=r + 1,
                   end_column=5)
    ws.row_dimensions[r + 1].height = 34

    ws.first_rate, ws.last_rate = 5, last
    return ws


# --------------------------------------------------------------------------
# 4. Quote Builder
# --------------------------------------------------------------------------
def sheet_quote(wb, cur, rate_ws, cost_ws):
    ws = wb.create_sheet("Quote Builder")
    _title(ws, "Quote Builder",
           "One job at a time. Cream cells are yours; everything else "
           "calculates.", 4)
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 3
    ws.column_dimensions["D"].width = 52

    fr, lr = rate_ws.first_rate, rate_ws.last_rate
    RC = f"'Rate Card'!$A${fr}:$E${lr}"

    def band(row, text):
        c = ws.cell(row=row, column=1, value=text)
        c.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        c.fill = FILL_HEAD
        c.border = BOX
        ws.cell(row=row, column=2).fill = FILL_HEAD
        ws.cell(row=row, column=2).border = BOX

    def label(row, text, note=None):
        c = ws.cell(row=row, column=1, value=text)
        c.font = BODY
        c.border = BOX
        if note:
            n = ws.cell(row=row, column=4, value=note)
            n.font = NOTE
            n.alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[row].height = max(
                ws.row_dimensions[row].height or 15, 30)

    def calc(row, text, formula, fmt, strong=False):
        c = ws.cell(row=row, column=1, value=text)
        c.font = BOLD if strong else BODY
        c.border = BOX
        v = ws.cell(row=row, column=2, value=formula)
        v.font = BOLD if strong else BODY
        v.border = BOX
        v.number_format = fmt
        if strong:
            c.fill = FILL_BAND
            v.fill = FILL_BAND
        return v

    r = 4
    band(r, "The job")
    r += 1
    label(r, "Customer")
    _input(ws, f"B{r}", "Example: J. Smith")
    r += 1
    label(r, "Type of work — copy a name from the Rate Card",
          "Must match a Rate Card row exactly, or the rate below reads zero.")
    _input(ws, f"B{r}", "Block paving / driveway")
    work_row = r
    r += 1
    label(r, "Measurement (in that row's unit)",
          "Square metres, feet, acres, windows, days — whatever that row "
          "says. The sheet does not assume a unit.")
    _input(ws, f"B{r}", 120, "#,##0.00")
    qty_row = r
    r += 1
    calc(r, "Rate from the Rate Card",
         f"=IF(ISERROR(VLOOKUP($B${work_row},{RC},3,FALSE)),0,"
         f"VLOOKUP($B${work_row},{RC},3,FALSE))",
         f'"{cur}"#,##0.00')
    rate_row = r
    r += 1
    calc(r, "Units per hour from the Rate Card",
         f"=IF(ISERROR(VLOOKUP($B${work_row},{RC},4,FALSE)),0,"
         f"VLOOKUP($B${work_row},{RC},4,FALSE))", "#,##0.00")
    uph_row = r
    r += 1
    # Without this the sheet is dangerous. A typo in the work-type name makes
    # both lookups return zero, the job prices at the minimum call-out with
    # zero hours, and the verdict reads "Worth doing" at 70% margin — a 113
    # quote for a job worth thousands, with nothing on screen to say so.
    label(r, "Work type found on the Rate Card?",
          "If this says NO, the name above does not match any Rate Card row "
          "and every number below it is wrong. Copy the name exactly.")
    found = ws.cell(
        row=r, column=2,
        value=f'=IF(ISERROR(VLOOKUP($B${work_row},{RC},3,FALSE)),'
              f'"NO — check the spelling","yes")')
    found.font = BOLD
    found.border = BOX
    found_row = r

    r += 2
    band(r, "Multipliers — price the risk, do not absorb it")
    r += 1
    label(r, "Access  (1.00 normal)",
          "Carrying kit upstairs, no parking, long hose runs, scaffold. "
          "1.15 to 1.40 is normal for awkward sites.")
    _input(ws, f"B{r}", 1.00, "0.00")
    access_row = r
    r += 1
    label(r, "Condition  (1.00 normal)",
          "How bad is it. Heavy moss, years of neglect, ground-in oil.")
    _input(ws, f"B{r}", 1.00, "0.00")
    cond_row = r
    r += 1
    label(r, "Unknowns  (1.00 you have seen all of it)",
          "The honest answer to \"how do you quote when you cannot see the "
          "whole job\". A roof you have not been on is 1.15 to 1.30. This "
          "is not padding — it is the cost of finding out on site.")
    _input(ws, f"B{r}", 1.00, "0.00")
    unk_row = r
    r += 1
    calc(r, "Combined multiplier",
         f"=B{access_row}*B{cond_row}*B{unk_row}", "0.000", strong=True)
    mult_row = r

    r += 2
    band(r, "Money out on this job")
    r += 1
    label(r, "Chemicals and consumables")
    _input(ws, f"B{r}", 24, f'"{cur}"#,##0.00')
    chem_row = r
    r += 1
    label(r, "Waste disposal / tip fees")
    _input(ws, f"B{r}", 0, f'"{cur}"#,##0.00')
    tip_row = r
    r += 1
    label(r, "Travel — round trip distance")
    _input(ws, f"B{r}", 18, "#,##0")
    dist_row = r
    r += 1
    label(r, "Cost per unit distance")
    _input(ws, f"B{r}", 0.55, f'"{cur}"#,##0.00')
    ppm_row = r
    r += 1
    label(r, "Hired help — total pay for this job")
    _input(ws, f"B{r}", 0, f'"{cur}"#,##0.00')
    help_row = r
    r += 1
    calc(r, "Total direct costs",
         f"=B{chem_row}+B{tip_row}+(B{dist_row}*B{ppm_row})+B{help_row}",
         f'"{cur}"#,##0.00', strong=True)
    direct_row = r

    r += 2
    band(r, "The quote")
    r += 1
    calc(r, "Hours on site",
         f"=IF(B{uph_row}=0,0,(B{qty_row}/B{uph_row})*B{mult_row})",
         "#,##0.00")
    hrs_row = r
    r += 1
    calc(r, "Work at rate",
         f"=B{qty_row}*B{rate_row}*B{mult_row}", f'"{cur}"#,##0.00')
    work_val_row = r
    r += 1
    label(r, "Minimum call-out charge",
          "The smallest amount worth turning up for. A job never prices "
          "below this.")
    _input(ws, f"B{r}", 80, f'"{cur}"#,##0.00')
    minimum_row = r
    r += 1
    calc(r, "Subtotal before costs",
         f"=MAX(B{work_val_row},B{minimum_row})", f'"{cur}"#,##0.00')
    sub_row = r
    r += 1
    label(r, "Discount  (0.00 = none, 0.10 = 10% off)")
    _input(ws, f"B{r}", 0, "0.00")
    disc_row = r
    r += 1
    calc(r, "PRICE TO QUOTE",
         f"=ROUND((B{sub_row}+B{direct_row})*(1-B{disc_row}),2)",
         f'"{cur}"#,##0.00')
    price_row = r
    p = ws.cell(row=price_row, column=2)
    p.font = BIG
    p.fill = FILL_ACC
    ws.cell(row=price_row, column=1).font = BIG
    ws.cell(row=price_row, column=1).fill = FILL_ACC
    ws.row_dimensions[price_row].height = 24

    r += 2
    band(r, "Is it actually worth doing")
    r += 1
    calc(r, "Your break-even hourly rate",
         f"={cost_ws.breakeven}", f'"{cur}"#,##0.00')
    r += 1
    calc(r, "Cost of your hours on this job",
         f"=B{hrs_row}*{cost_ws.breakeven}", f'"{cur}"#,##0.00')
    hourcost_row = r
    r += 1
    calc(r, "Profit after costs and your own time",
         f"=B{price_row}-B{direct_row}-B{hourcost_row}",
         f'"{cur}"#,##0.00', strong=True)
    profit_row = r
    r += 1
    calc(r, "Margin",
         f"=IF(B{price_row}=0,0,B{profit_row}/B{price_row})",
         "0.0%", strong=True)
    margin_row = r
    r += 1
    calc(r, "Effective hourly rate on this job",
         f"=IF(B{hrs_row}=0,0,(B{price_row}-B{direct_row})/B{hrs_row})",
         f'"{cur}"#,##0.00', strong=True)
    eff_row = r
    r += 1
    v = ws.cell(row=r, column=1, value="Verdict")
    v.font = BOLD
    v.border = BOX
    verdict = ws.cell(
        row=r, column=2,
        value=f'=IF(B{found_row}<>"yes",'
              f'"Work type not on the Rate Card — fix that first",'
              f'IF(B{price_row}=0,"Fill the job in above",'
              f'IF(B{profit_row}<0,"LOSES MONEY — requote or walk away",'
              f'IF(B{margin_row}<0.15,"Thin — one problem on site wipes it out",'
              f'"Worth doing"))))')
    verdict.font = BOLD
    verdict.border = BOX
    ws.cell(row=r, column=4,
            value="This compares the quote against your own break-even, so "
                  "it is your verdict, not a generic one.").font = NOTE
    ws.cell(row=r, column=4).alignment = Alignment(wrap_text=True,
                                                   vertical="top")

    ws.rows_map = dict(found=found_row, work=work_row, qty=qty_row, rate=rate_row,
                       uph=uph_row, access=access_row, cond=cond_row,
                       unk=unk_row, mult=mult_row, chem=chem_row,
                       tip=tip_row, dist=dist_row, ppm=ppm_row,
                       help=help_row, direct=direct_row, hrs=hrs_row,
                       work_val=work_val_row, minimum=minimum_row,
                       sub=sub_row, disc=disc_row, price=price_row,
                       hourcost=hourcost_row, profit=profit_row,
                       margin=margin_row, eff=eff_row)
    return ws


# --------------------------------------------------------------------------
# 5. Quote Log
# --------------------------------------------------------------------------
def sheet_log(wb, cur, rows=60):
    ws = wb.create_sheet("Quote Log")
    _title(ws, "Quote Log",
           "Every quote you send, won or lost. This is the tab that tells "
           "you which work to stop quoting for.", 8)
    _header(ws, 4, ["Date", "Customer", "Type of work", "Price quoted",
                    "Hours", "Effective hourly", "Won?", "Notes"],
            [12, 22, 30, 15, 10, 16, 9, 34])
    for r in range(5, 5 + rows):
        for col in range(1, 9):
            c = ws.cell(row=r, column=col)
            c.border = BOX
            c.fill = FILL_IN
        ws.cell(row=r, column=1).number_format = "yyyy-mm-dd"
        ws.cell(row=r, column=4).number_format = f'"{cur}"#,##0.00'
        ws.cell(row=r, column=5).number_format = "#,##0.00"
        f = ws.cell(row=r, column=6,
                    value=f"=IF(E{r}=0,\"\",D{r}/E{r})")
        f.number_format = f'"{cur}"#,##0.00'
        f.font = BOLD
        f.border = BOX

    first, last = 5, 4 + rows
    r = last + 2
    ws.cell(row=r, column=2, value="Quotes sent").font = BOLD
    ws.cell(row=r, column=4, value=f"=COUNT(D{first}:D{last})").font = BOLD
    ws.cell(row=r + 1, column=2, value="Quotes won").font = BOLD
    ws.cell(row=r + 1, column=4,
            value=f'=COUNTIF(G{first}:G{last},"y")').font = BOLD
    ws.cell(row=r + 2, column=2, value="Win rate").font = BOLD
    wr = ws.cell(row=r + 2, column=4,
                 value=f'=IF(COUNT(D{first}:D{last})=0,0,'
                       f'COUNTIF(G{first}:G{last},"y")/COUNT(D{first}:D{last}))')
    wr.font = BOLD
    wr.number_format = "0.0%"
    ws.cell(row=r + 3, column=2, value="Value won").font = BOLD
    vw = ws.cell(row=r + 3, column=4,
                 value=f'=SUMIF(G{first}:G{last},"y",D{first}:D{last})')
    vw.font = BOLD
    vw.number_format = f'"{cur}"#,##0.00'
    ws.cell(row=r + 5, column=2,
            value="Mark the Won? column y or n. A win rate near 100% usually "
                  "means you are too cheap, not that you are good at "
                  "quoting.").font = NOTE
    ws.log_rows = (first, last)
    return ws


def build(path, currency):
    wb = Workbook()
    wb.remove(wb.active)
    sheet_start(wb)
    costs = sheet_costs(wb, currency)
    rates = sheet_rates(wb, currency)
    sheet_quote(wb, currency, rates, costs)
    sheet_log(wb, currency)
    wb.save(path)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--out", default="Job-Pricing-Quoting-Calculator.xlsx")
    ap.add_argument("--currency", default="$",
                    help="symbol used in number formats (default $)")
    args = ap.parse_args()
    print("built ->", build(args.out, args.currency))


if __name__ == "__main__":
    main()
