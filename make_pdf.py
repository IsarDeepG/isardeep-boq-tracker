#!/usr/bin/env python3
"""Item-wise Isardeep interior BOQ status PDF from live shared JSON + page items."""
import json
import math
from pathlib import Path

from fpdf import FPDF

HTML = Path("/workspace/isardeep-boq/index.html").read_text(encoding="utf-8")
_items_js = HTML.split("const ITEMS = ", 1)[1]
if ";\nconst DISCOUNT" in _items_js:
    _items_js = _items_js.split(";\nconst DISCOUNT", 1)[0]
else:
    _items_js = _items_js.split(";\nconst money", 1)[0]
items = json.loads(_items_js)
state = json.loads(Path("/tmp/boq.json").read_text(encoding="utf-8"))["lines"]

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONTB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def js_round(n):
    return int(math.floor(n + 0.5)) if n >= 0 else int(math.ceil(n - 0.5))


DISC = 0.85


def amount_mrp(it):
    if it["id"] == "001":
        return 13650
    a = it.get("amount")
    if a is None or a == "" or float(a) == 0:
        return None
    return int(a) if float(a) == int(a) else float(a)


def amount_of(it):
    """Line amount after 15% discount (nearest rupee)."""
    a = amount_mrp(it)
    if a is None:
        return None
    return js_round(a * DISC)


def status_of(it):
    rec = state.get(it["id"]) or {}
    return rec.get("status") or ""


def comment_of(it):
    rec = state.get(it["id"]) or {}
    return (rec.get("comment") or "").strip()


def split_cost(it):
    a = amount_of(it)
    if a is None:
        return None
    st = status_of(it)
    if st == "done":
        return a, 0
    if st == "partial":
        on = js_round(a * 0.5)
        return on, a - on
    if st == "unfinished":
        on = js_round(a * 0.8)
        return on, a - on
    if st == "pending":
        return 0, a
    return 0, 0


def inr(n):
    n = int(n)
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) <= 3:
        body = s
    else:
        body = s[-3:]
        s = s[:-3]
        parts = []
        while s:
            parts.append(s[-2:])
            s = s[:-2]
        body = ",".join(reversed(parts)) + "," + body
    return sign + "₹" + body


def money_or_dash(n):
    return "—" if n is None else inr(n)


LABEL = {
    "done": "Done",
    "partial": "Partial",
    "unfinished": "Unfinished",
    "pending": "Pending",
    "skip": "Skip",
    "": "Not set",
}

printed_on = printed_pend = 0
louvers_on = louvers_pend = 0
for it in items:
    sp = split_cost(it)
    if not sp or status_of(it) == "skip":
        continue
    if it["id"] == "001":
        louvers_on, louvers_pend = sp
        continue
    printed_on += sp[0]
    printed_pend += sp[1]

# widths mm, landscape A4 content width 273 (297 - 12 - 12)
W = [92, 34, 28, 34, 34, 51]
HEADERS = ["Item", "BOQ amount", "Status", "On site", "Pending", "Comment"]


class PDF(FPDF):
    def footer(self):
        self.set_y(-10)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(80, 80, 80)
        self.cell(0, 5, f"Isardeep interior BOQ  ·  3 Oct 2026 (Asia/Kolkata)  ·  Page {self.page_no()}/{{nb}}", align="C")


pdf = PDF(orientation="L", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=14)
pdf.add_font("DejaVu", "", FONT)
pdf.add_font("DejaVu", "B", FONTB)
pdf.alias_nb_pages()
pdf.set_margins(12, 12, 12)
pdf.add_page()


def ensure(h):
    if pdf.get_y() + h > pdf.h - 14:
        pdf.add_page()
        draw_col_header()


def text_lines(text, width, size, bold=False):
    pdf.set_font("DejaVu", "B" if bold else "", size)
    return pdf.multi_cell(width, 3.6, text or "", dry_run=True, output="LINES")


def draw_cells(cells, widths, size=8, bold=False, fill=None, ink=(28, 25, 21), min_h=6.2, align=None):
    align = align or ["L"] * len(cells)
    pdf.set_font("DejaVu", "B" if bold else "", size)
    line_sets = []
    for text, w in zip(cells, widths):
        line_sets.append(pdf.multi_cell(w - 1.6, 3.6, str(text), dry_run=True, output="LINES"))
    h = max(min_h, max(len(ls) for ls in line_sets) * 3.6 + 1.4)
    ensure(h)
    # ensure() may have added a page and a header; recompute y
    y = pdf.get_y()
    x = pdf.l_margin
    if fill:
        pdf.set_fill_color(*fill)
    pdf.set_draw_color(210, 202, 188)
    pdf.set_text_color(*ink)
    for text, w, al in zip(cells, widths, align):
        pdf.rect(x, y, w, h, style="DF" if fill else "D")
        pdf.set_xy(x + 0.8, y + 0.6)
        pdf.multi_cell(w - 1.6, 3.6, str(text), align=al, new_x="RIGHT", new_y="TOP")
        x += w
    pdf.set_xy(pdf.l_margin, y + h)


def draw_col_header():
    draw_cells(HEADERS, W, size=8, bold=True, fill=(28, 25, 21), ink=(255, 255, 255), min_h=6.4,
               align=["L", "R", "L", "R", "R", "L"])


pdf.set_text_color(28, 25, 21)
pdf.set_font("DejaVu", "B", 16)
pdf.cell(0, 8, "Isardeep interior BOQ", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("DejaVu", "", 10)
pdf.set_text_color(70, 64, 56)
pdf.cell(0, 6, "3 Oct 2026 (Asia/Kolkata)", new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)
pdf.set_font("DejaVu", "B", 11)
pdf.set_text_color(28, 107, 67)
pdf.cell(0, 6, f"On site (after 15% discount, printed BOQ): {inr(printed_on)}", new_x="LMARGIN", new_y="NEXT")
pdf.set_text_color(138, 59, 18)
pdf.cell(0, 6, f"Still pending (after 15% discount, printed BOQ): {inr(printed_pend)}", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("DejaVu", "", 9)
pdf.set_text_color(70, 64, 56)
louvers_disc = amount_of({"id": "001", "amount": None})
pdf.multi_cell(
    0,
    4.4,
    "Amounts after 15% discount. GST 18% not included. Louvers are not on the printed BOQ, "
    "so they are not in the two totals above. "
    f"Agreed MRP {inr(13650)} → {inr(louvers_disc)} after discount (65 sq ft × ₹210). "
    f"Status partial — 50% on site / 50% pending (on site {inr(louvers_on)}, pending {inr(louvers_pend)}). "
    f"Live tracker hero: on site {inr(printed_on + louvers_on)}, "
    f"still pending {inr(printed_pend + louvers_pend)}.",
)
pdf.ln(1)
pdf.set_font("DejaVu", "", 8)
pdf.multi_cell(
    0,
    3.8,
    "Done = 100% on site. Partial = 50% on site / 50% pending. Unfinished = 80% on site / 20% pending. "
    "Pending = 100% pending. Skip is left out of both totals and listed at the end. "
    "Lines with no amount are status only (rupee columns —).",
)
pdf.ln(2)

draw_col_header()

skipped = []
last_room = None
for it in items:
    st = status_of(it)
    if st == "skip":
        skipped.append(it)
        continue
    if it["room"] != last_room:
        last_room = it["room"]
        draw_cells([it["room"], "", "", "", "", ""], W, size=9, bold=True, fill=(243, 239, 230), min_h=6.2)
    a = amount_of(it)
    sp = split_cost(it)
    # skip already excluded; unset/no amount
    if a is None or sp is None:
        on_s, pend_s = "—", "—"
        boq_s = "—"
    else:
        boq_s = inr(a)
        on_s, pend_s = inr(sp[0]), inr(sp[1])
    name = f"{it['id']}  {it['name']}"
    draw_cells(
        [name, boq_s, LABEL.get(st, st), on_s, pend_s, comment_of(it)],
        W,
        size=8,
        align=["L", "R", "L", "R", "R", "L"],
    )

pdf.ln(3)
pdf.set_font("DejaVu", "B", 12)
pdf.set_text_color(28, 25, 21)
if pdf.get_y() > pdf.h - 40:
    pdf.add_page()
pdf.cell(0, 7, "Skipped (not in the two totals)", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("DejaVu", "", 8)
pdf.set_text_color(70, 64, 56)
pdf.cell(0, 4.5, "These lines are marked skip and are excluded from on site and still pending.", new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)
draw_col_header()
if not skipped:
    draw_cells(["None", "—", "—", "—", "—", ""], W, size=8)
else:
    for it in skipped:
        a = amount_of(it)
        draw_cells(
            [f"{it['id']}  {it['name']}  ·  {it['room']}", money_or_dash(a), "Skip", "—", "—", comment_of(it)],
            W,
            size=8,
            align=["L", "R", "L", "R", "R", "L"],
        )

out = Path("/workspace/isardeep-boq/isardeep-boq-status.pdf")
pdf.output(str(out))
print("pages", pdf.pages_count)
print("printed_on", int(printed_on), inr(printed_on))
print("printed_pend", int(printed_pend), inr(printed_pend))
print("louvers", int(louvers_on), int(louvers_pend))
print("tracker", int(printed_on + louvers_on), int(printed_pend + louvers_pend))
print("bytes", out.stat().st_size)
