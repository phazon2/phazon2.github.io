#!/usr/bin/env python3
"""Build the 12-Month Bookkeeping Workbook — the sample product for Realistic Bookkeeping.

Design decision worth recording: her free template uses 12 duplicated monthly tabs
joined by SUMIF, and that architecture is what her commenters keep breaking on:

  "stuck on creating a formula to add up 12 sheets for the final totals"
  "I created duplicates for each month... how does it know which month to pull from?"
  "the sumif formula for my profit and loss statement... would not cross over"

So this does not scale her template up. It replaces the 12 tabs with ONE ledger and
derives the month from the date, which is what makes an annual rollup a single SUMIFS
instead of a twelve-sheet chain. The question "how does it know which month" stops
existing rather than getting answered.

Also covered, each traceable to a real comment on that video:
  - sales tax tracking          ("could you do a video on figuring sales tax")
  - expense categories by month ("How do you breakout the expense categories by month?")
  - works in Excel and Sheets   ("I was following along in Excel... please do it in excel")
"""

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ARIAL = "Arial"
BLUE = "0000FF"      # cells the user types into
BLACK = "000000"     # formulas
GREEN = "008000"     # cross-sheet links
YELLOW = "FFFF00"    # fill in
INK = "1F3A4D"
RULE = Side(style="thin", color="BFC9D1")
MONEY = '$#,##0.00;($#,##0.00);-'
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

INCOME_CATS = ["Sales - Products", "Sales - Services", "Other Income"]
EXPENSE_CATS = [
    "Advertising", "Bank & Merchant Fees", "Contract Labor", "Dues & Subscriptions",
    "Insurance", "Meals (50% deductible)", "Office Supplies", "Professional Fees",
    "Rent or Lease", "Repairs & Maintenance", "Software", "Supplies - Materials",
    "Taxes & Licenses", "Travel", "Utilities", "Vehicle & Mileage", "Other Expenses",
]

# One realistic example row per required format, as the skill requires for a
# fill-in workbook. Dates are text-free real dates so MONTH() resolves.
import datetime as dt
EXAMPLES = [
    (dt.date(2026, 1, 4),  "Etsy payout - Dec orders", "Sales - Products",   "Income",  1240.50, "Etsy deposit"),
    (dt.date(2026, 1, 9),  "Canva Pro annual",         "Software",           "Expense",  119.00, "Card 4412"),
    (dt.date(2026, 1, 17), "Packaging - 500 mailers",  "Supplies - Materials", "Expense", 214.86, "Card 4412"),
    (dt.date(2026, 2, 2),  "Bookkeeping client - Feb", "Sales - Services",   "Income",   450.00, "Zelle"),
    (dt.date(2026, 2, 14), "Stripe processing fees",    "Bank & Merchant Fees", "Expense",  38.42, "Auto-deducted"),
    (dt.date(2026, 3, 1),  "Studio rent - March",      "Rent or Lease",      "Expense",  600.00, "ACH"),
]


def style(cell, *, bold=False, size=11, color=BLACK, fill=None, fmt=None,
          align=None, wrap=False, border=False):
    cell.font = Font(name=ARIAL, bold=bold, size=size, color=color)
    if fill:
        cell.fill = PatternFill("solid", start_color=fill, end_color=fill)
    if fmt:
        cell.number_format = fmt
    if align or wrap:
        cell.alignment = Alignment(horizontal=align, vertical="center", wrap_text=wrap)
    if border:
        cell.border = Border(bottom=RULE, top=RULE, left=RULE, right=RULE)
    return cell


def title(ws, text, sub=None, span=8):
    style(ws["A1"], bold=True, size=16, color=INK).value = text
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=span)
    if sub:
        style(ws["A2"], size=10, color="5A6B77", wrap=True,
              align="left").value = sub
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=span)
        ws.row_dimensions[2].height = 28
    ws.row_dimensions[1].height = 26


# ---------------------------------------------------------------- Start Here
def sheet_start(wb):
    ws = wb.create_sheet("Start Here")
    title(ws, "12-Month Bookkeeping Workbook",
          "One ledger for the whole year. Type every transaction on the Transactions tab; "
          "every other tab updates itself.", span=2)
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 78

    rows = [
        ("HOW TO USE", ""),
        ("1. Transactions tab",
         "Enter one row per transaction: date, description, category, income or expense, amount. "
         "That is the only tab you type in."),
        ("2. Month fills itself",
         "The Month column reads the date. You never pick a month, and you never duplicate a tab "
         "for a new month — which is what makes the annual total work."),
        ("3. Monthly P&L tab",
         "Every category by month, with a Year-to-Date column at the right. Updates as you type."),
        ("4. Sales Tax tab",
         "Enter your rate once. Taxable sales and tax owed are calculated per month."),
        ("", ""),
        ("WHAT THE COLOURS MEAN", ""),
        ("Blue text on yellow fill", "You type here."),
        ("Black text", "A formula. Leave it alone and it stays correct."),
        ("Green text", "Pulls from another tab."),
        ("", ""),
        ("ADDING YOUR OWN CATEGORIES", ""),
        ("Categories tab",
         "Add or rename categories there, then add the same name to column A of the Monthly P&L "
         "tab and copy the formula across. Nothing else needs changing."),
        ("", ""),
        ("EXCEL AND GOOGLE SHEETS", ""),
        ("Both work",
         "Built with standard functions (SUMIFS, MONTH, IFERROR). Open it in Excel, or upload to "
         "Google Drive and open with Sheets — the formulas carry over unchanged."),
        ("", ""),
        ("ONE ASSUMPTION TO CHECK", ""),
        ("Tax year",
         "The example rows are dated 2026 and the Monthly P&L covers one calendar year. If your "
         "books run on a different fiscal year, the month columns still work — only the label changes."),
    ]
    r = 4
    for label, body in rows:
        if label and not body:
            style(ws.cell(r, 1), bold=True, size=10, color=INK).value = label
        elif label:
            style(ws.cell(r, 1), bold=True).value = label
            style(ws.cell(r, 2), wrap=True).value = body
            ws.row_dimensions[r].height = 30
        r += 1

    style(ws.cell(r + 1, 1), size=9, color="8A97A0", wrap=True).value = (
        "Sample built for Realistic Bookkeeping from questions asked on the channel. "
        "Example rows are illustrative figures, not real business data — delete them before you start.")
    return ws


# ------------------------------------------------------------------ Categories
def sheet_categories(wb):
    ws = wb.create_sheet("Categories")
    title(ws, "Categories",
          "Edit, rename or add. Used by the Monthly P&L rollups — a name here must match the "
          "name in column A of that tab.", span=2)
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 30

    style(ws["A4"], bold=True, fill="E8EEF1", border=True).value = "Income categories"
    style(ws["B4"], bold=True, fill="E8EEF1", border=True).value = "Expense categories"
    for i, c in enumerate(INCOME_CATS):
        style(ws.cell(5 + i, 1), color=BLUE, fill=YELLOW, border=True).value = c
    for i, c in enumerate(EXPENSE_CATS):
        style(ws.cell(5 + i, 2), color=BLUE, fill=YELLOW, border=True).value = c
    return ws


# ---------------------------------------------------------------- Transactions
def sheet_transactions(wb, n_rows=200):
    ws = wb.create_sheet("Transactions")
    title(ws, "Transactions",
          "One row per transaction, all twelve months in this single tab. The Month column is a "
          "formula — it reads the date, so nothing has to be sorted or split by month.", span=8)

    heads = ["Date", "Month", "Description", "Category", "Income or Expense",
             "Amount", "Payment method", "Notes"]
    widths = [12, 9, 38, 24, 18, 14, 18, 26]
    for i, (h, w) in enumerate(zip(heads, widths), start=1):
        style(ws.cell(4, i), bold=True, color="FFFFFF", fill=INK, border=True,
              align="center", wrap=True).value = h
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[4].height = 30

    for i, (d, desc, cat, kind, amt, note) in enumerate(EXAMPLES):
        r = 5 + i
        style(ws.cell(r, 1), color=BLUE, fmt="yyyy-mm-dd", border=True).value = d
        style(ws.cell(r, 3), color=BLUE, border=True).value = desc
        style(ws.cell(r, 4), color=BLUE, border=True).value = cat
        style(ws.cell(r, 5), color=BLUE, border=True).value = kind
        style(ws.cell(r, 6), color=BLUE, fmt=MONEY, border=True).value = amt
        style(ws.cell(r, 7), color=BLUE, border=True).value = note

    # Month formula down the whole range — this is the piece that replaces 12 tabs.
    for r in range(5, 5 + n_rows):
        style(ws.cell(r, 2), border=True, align="center").value = \
            f'=IF($A{r}="","",MONTH($A{r}))'
        if r >= 5 + len(EXAMPLES):
            for col in (1, 3, 4, 5, 6, 7, 8):
                fmt = "yyyy-mm-dd" if col == 1 else (MONEY if col == 6 else None)
                style(ws.cell(r, col), color=BLUE, fill=YELLOW, fmt=fmt, border=True)

    ws.freeze_panes = "A5"
    return ws


# ---------------------------------------------------------------- Monthly P&L
def sheet_pnl(wb, tx_rows=204):
    ws = wb.create_sheet("Monthly P&L")
    title(ws, "Monthly Profit & Loss",
          "Every category by month, with a Year-to-Date column. All formulas — it fills in as you "
          "type on the Transactions tab.", span=14)

    ws.column_dimensions["A"].width = 28
    style(ws.cell(4, 1), bold=True, color="FFFFFF", fill=INK, border=True).value = "Category"
    # Row 5 carries the month NUMBER each column matches on. Visible on purpose:
    # it is the answer to "how does it know which month to pull from".
    style(ws.cell(5, 1), size=9, color="8A97A0", align="right").value = "month number →"
    for i, m in enumerate(MONTHS):
        c = 2 + i
        style(ws.cell(4, c), bold=True, color="FFFFFF", fill=INK, border=True, align="center").value = m
        style(ws.cell(5, c), size=9, color="8A97A0", align="center").value = i + 1
        ws.column_dimensions[get_column_letter(c)].width = 12
    ytd = 14
    style(ws.cell(4, ytd), bold=True, color="FFFFFF", fill="2E6E6E", border=True,
          align="center", wrap=True).value = "Year to Date"
    ws.column_dimensions[get_column_letter(ytd)].width = 15

    lo, hi = 5, tx_rows

    def block(start_row, label, cats):
        style(ws.cell(start_row, 1), bold=True, size=11, color=INK, fill="E8EEF1",
              border=True).value = label
        for c in range(2, ytd + 1):
            style(ws.cell(start_row, c), fill="E8EEF1", border=True)
        r = start_row + 1
        for cat in cats:
            style(ws.cell(r, 1), color=GREEN, border=True).value = cat
            for i in range(12):
                c = 2 + i
                col = get_column_letter(c)
                style(ws.cell(r, c), fmt=MONEY, border=True).value = (
                    f"=SUMIFS(Transactions!$F${lo}:$F${hi},"
                    f"Transactions!$B${lo}:$B${hi},{col}$5,"
                    f"Transactions!$D${lo}:$D${hi},$A{r})"
                )
            style(ws.cell(r, ytd), fmt=MONEY, bold=True, border=True).value = \
                f"=SUM(B{r}:M{r})"
            r += 1
        # subtotal
        style(ws.cell(r, 1), bold=True, border=True).value = f"Total {label.lower()}"
        for c in range(2, ytd + 1):
            cl = get_column_letter(c)
            style(ws.cell(r, c), bold=True, fmt=MONEY, border=True).value = \
                f"=SUM({cl}{start_row + 1}:{cl}{r - 1})"
        return r

    inc_total = block(7, "INCOME", INCOME_CATS)
    exp_total = block(inc_total + 2, "EXPENSES", EXPENSE_CATS)

    net = exp_total + 2
    style(ws.cell(net, 1), bold=True, size=12, color="FFFFFF", fill="2E6E6E",
          border=True).value = "NET PROFIT"
    for c in range(2, ytd + 1):
        cl = get_column_letter(c)
        style(ws.cell(net, c), bold=True, size=12, color="FFFFFF", fill="2E6E6E",
              fmt=MONEY, border=True).value = f"={cl}{inc_total}-{cl}{exp_total}"

    note = net + 2
    style(ws.cell(note, 1), size=9, color="8A97A0", wrap=True).value = (
        "Each month column matches on the month number in row 5 and the category in column A. "
        "That is why there is no separate tab per month, and why the Year-to-Date column is a "
        "plain SUM rather than a chain across twelve sheets.")
    ws.merge_cells(start_row=note, start_column=1, end_row=note, end_column=ytd)
    ws.row_dimensions[note].height = 28

    ws.freeze_panes = "B6"
    return ws


# ------------------------------------------------------------------ Sales Tax
def sheet_tax(wb, tx_rows=204):
    ws = wb.create_sheet("Sales Tax")
    title(ws, "Sales Tax",
          "Enter your rate once; taxable sales and tax owed are calculated per month.", span=5)
    ws.column_dimensions["A"].width = 24
    for c in range(2, 6):
        ws.column_dimensions[get_column_letter(c)].width = 16

    style(ws["A4"], bold=True).value = "Your sales tax rate"
    style(ws["B4"], color=BLUE, fill=YELLOW, fmt="0.00%", border=True).value = 0.0725
    style(ws["C4"], size=9, color="8A97A0").value = "← type your rate here (7.25% shown)"

    style(ws["A5"], bold=True).value = "Taxable categories"
    style(ws["B5"], color=BLUE, fill=YELLOW, border=True).value = "Sales - Products"
    style(ws["C5"], size=9, color="8A97A0").value = "← which income category is taxable"

    heads = ["Month", "Taxable sales", "Tax collected", "Running total"]
    for i, h in enumerate(heads, start=1):
        style(ws.cell(7, i), bold=True, color="FFFFFF", fill=INK, border=True,
              align="center").value = h

    lo, hi = 5, tx_rows
    for i, m in enumerate(MONTHS):
        r = 8 + i
        style(ws.cell(r, 1), border=True).value = m
        style(ws.cell(r, 2), fmt=MONEY, color=GREEN, border=True).value = (
            f"=SUMIFS(Transactions!$F${lo}:$F${hi},"
            f"Transactions!$B${lo}:$B${hi},{i + 1},"
            f"Transactions!$D${lo}:$D${hi},$B$5)"
        )
        style(ws.cell(r, 3), fmt=MONEY, border=True).value = f"=B{r}*$B$4"
        style(ws.cell(r, 4), fmt=MONEY, border=True).value = (
            f"=C8" if i == 0 else f"=D{r - 1}+C{r}")

    tot = 20
    style(ws.cell(tot, 1), bold=True, border=True).value = "Year total"
    style(ws.cell(tot, 2), bold=True, fmt=MONEY, border=True).value = "=SUM(B8:B19)"
    style(ws.cell(tot, 3), bold=True, fmt=MONEY, border=True).value = "=SUM(C8:C19)"

    style(ws.cell(22, 1), size=9, color="8A97A0", wrap=True).value = (
        "Assumption: a single flat rate on one taxable category. If you sell into several "
        "jurisdictions, or some products are exempt, this tab needs a rate per jurisdiction — "
        "it is not a substitute for advice from your own tax preparer.")
    ws.merge_cells("A22:E22")
    ws.row_dimensions[22].height = 30
    return ws


def main():
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    sheet_start(wb)
    sheet_transactions(wb)
    sheet_pnl(wb)
    sheet_tax(wb)
    sheet_categories(wb)
    for ws in wb:
        ws.sheet_view.showGridLines = False
    out = "12-Month-Bookkeeping-Workbook-SAMPLE.xlsx"
    wb.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
