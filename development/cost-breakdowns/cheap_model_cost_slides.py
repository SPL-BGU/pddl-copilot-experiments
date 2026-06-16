#!/usr/bin/env python3
"""Self-contained cost-breakdown deck (5 slides) for the CHEAP-model API
baseline: 2 models over BOTH benchmarks (PlanBench full + sweep5 single-tool),
both think on/off, full corpus. Slide 5 adds the DEPLOYMENT alternative we lean
toward for the OPEN-model roster: rent one steady neocloud GPU (H200-141GB) and
self-host with vanilla vLLM instead of queuing on the 3090/RTX-6000 cluster.

Style matches frontier_cost_slide.py (navy header, zebra rows, highlight). Unlike
that one, numbers are COMPUTED from the measured per-task token table below, so the
deck is reproducible — edit the data, re-run, the slides update.

Token source: canonical sweep5v2 corpus (Qwen3.5-9B), results/sweep5-cluster-20260601,
cumulative-across-loop prompt/completion tokens. Real for Qwen; PROXY for the closed
models (Opus-class tokenizer +~35% input; Claude/Gemini extended-thinking output may
be 2-5x on think-on cells). PlanBench tokens are the aggregate per-instance proxy from
development/claude_baseline_cost_estimate.md.
Pricing (per MTok in/out): Claude authoritative (claude-api skill); Gemini/Qwen from
web, June 2026 (tokenmix.ai, pricepertoken.com, aiapi-pro.com) — re-verify in-console.

    Run:  .venv/bin/python development/cost-breakdowns/cheap_model_cost_slides.py
    Out:  development/cost-breakdowns/cheap_model_cost_slides.pptx
"""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

# ---------------------------------------------------------------- palette
NAVY   = RGBColor(0x33, 0x55, 0x88)
INK    = RGBColor(0x1F, 0x30, 0x50)
GREY   = RGBColor(0x55, 0x55, 0x55)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
HILITE = RGBColor(0xE2, 0xF0, 0xD9)   # recommended / lean row
BAND   = RGBColor(0xF2, 0xF5, 0xFA)   # zebra band
RED    = RGBColor(0xA0, 0x30, 0x30)   # the dominant-cost flag

# ---------------------------------------------------------------- DATA
# task -> {cell: (mean_in, mean_out, n_per_cell)}  cell in {nt_off,nt_on,wt_off,wt_on}
T = {
 "solve":            {"nt_off":(1170,3746,300),"nt_on":(1168,5611,300),"wt_off":(17674,2347,600),"wt_on":(14107,5782,600)},
 "validate_domain":  {"nt_off":(794,1580,360), "nt_on":(792,5888,360), "wt_off":(9258,728,720),  "wt_on":(9784,1550,720)},
 "validate_problem": {"nt_off":(1148,940,600), "nt_on":(1146,5712,600),"wt_off":(11777,1381,1200),"wt_on":(11218,2421,1200)},
 "validate_plan":    {"nt_off":(1354,1771,3000),"nt_on":(1352,5755,3000),"wt_off":(12383,1441,6000),"wt_on":(11162,3359,6000)},
 "simulate":         {"nt_off":(1435,3215,300),"nt_on":(1432,5686,300),"wt_off":(16586,2126,600),"wt_on":(15502,2654,600)},
}
TASK_LABEL = {"solve":"solve","validate_domain":"validate_domain","validate_problem":"validate_problem",
              "validate_plan":"validate_plan","simulate":"simulate"}

# pricing $/MTok (in, out)
P = {"Qwen-Flash":(0.05,0.40), "Gemini Flash-Lite":(0.25,1.50), "Haiku 4.5":(1.0,5.0), "Sonnet 4.6":(3.0,15.0)}
PRICE_LBL = {"Qwen-Flash":"$0.05 / $0.40","Gemini Flash-Lite":"$0.25 / $1.50","Haiku 4.5":"$1 / $5","Sonnet 4.6":"$3 / $15"}
MODELS = ["Haiku 4.5", "Gemini Flash-Lite", "Sonnet 4.6", "Qwen-Flash"]

# PlanBench aggregate per-instance proxy; 7000 instances per cell, 4 cells
PB = {"nt_off":(1353,2056),"nt_on":(1274,5746),"wt_off":(12681,1482),"wt_on":(11540,3206)}
PB_N = 7000

# ---------------------------------------------------------------- cost engine
def _kk(arm, disc):
    if not disc: return 1.0, 1.0
    if arm == "nt": return 0.5, 0.5      # no-tools single-shot -> Batch -50% both
    return 0.505, 1.0                    # with-tools multi-turn -> caching on input only

def cost(mi, mo, n, pin, pout, arm, disc):
    ki, ko = _kk(arm, disc)
    return n * (mi*pin*ki + mo*pout*ko) / 1e6

def sweep5_task_totals(model, disc=True):
    pin, pout = P[model]; out = {}
    for task, cells in T.items():
        out[task] = sum(cost(mi,mo,n,pin,pout,"nt" if c[:2]=="nt" else "wt",disc)
                        for c,(mi,mo,n) in cells.items())
    return out

def sweep5_total(model, disc=True): return sum(sweep5_task_totals(model, disc).values())

def task_token_means(task):
    cells = T[task]; ntok = sum(n for _,_,n in cells.values())
    ai = sum(mi*n for mi,_,n in cells.values())/ntok
    ao = sum(mo*n for _,mo,n in cells.values())/ntok
    return ntok, ai, ao

def planbench_total(model, disc=True):
    pin, pout = P[model]
    return sum(cost(mi,mo,PB_N,pin,pout,"nt" if c[:2]=="nt" else "wt",disc) for c,(mi,mo) in PB.items())

def sweep5_scaled(model, vp_fix=10, dom_frac=1.0, wt_var=6, nt_var=3, think_both=True, disc=True):
    pin, pout = P[model]; tot = 0
    for task, cells in T.items():
        for c, (mi, mo, n) in cells.items():
            if c.endswith("on") and not think_both: continue
            arm = "nt" if c[:2] == "nt" else "wt"
            base_var = 3 if arm == "nt" else 6
            scale = ((nt_var if arm=="nt" else wt_var)/base_var) * dom_frac
            if task == "validate_plan": scale *= vp_fix/10.0
            tot += cost(mi, mo, n*scale, pin, pout, arm, disc)
    return tot

def money(x): return f"${x:,.0f}"

# ---------------------------------------------------------------- GPU-RENTAL DATA
# Alternative to the API baseline (slides 1-4): rent ONE persistent neocloud GPU,
# self-host the OPEN-model roster with vanilla vLLM, time-share the box across all
# five models (load one, run its cells, swap to next). Motivation: the free
# 3090/RTX-6000 SLURM cluster is queued and can't seat the 35B in BF16.
# Numbers below are ESTIMATES from the deployment handoff — confirm with a pilot.
GPU = {  # name -> ($/hr, BF16-fit note)
    "H200-141GB": (3.00, "all 5 single-GPU, clean BF16"),
    "H100-80GB":  (2.40, "<=9B clean; 31-35B need FP8 or TP=2"),
}
GPU_HRS = (40, 50)   # est. GPU-hours for the full sweep5v2 across all 5 (time-shared)
# Open-model roster (served one at a time) -> approx BF16 weight GB (~2 bytes/param)
ROSTER = [
    ("Qwen3.5-0.8B", 1.6),
    ("Qwen3.5-4B",   8),
    ("Qwen3.5-9B",   18),
    ("Qwen3.6-35B",  70),
    ("gemma4-31B †", 62),   # optional 5th model
]

def gpu_band(name):
    rate = GPU[name][0]
    return rate * GPU_HRS[0], rate * GPU_HRS[1]

def money_band(lo, hi): return f"${lo:,.0f}-{hi:,.0f}"

# ---------------------------------------------------------------- pptx helpers
def _set(cell, text, *, size, bold=False, color=INK, align=PP_ALIGN.LEFT, fill=None):
    cell.margin_left = Inches(0.06); cell.margin_right = Inches(0.06)
    cell.margin_top = Inches(0.02); cell.margin_bottom = Inches(0.02)
    if fill is not None:
        cell.fill.solid(); cell.fill.fore_color.rgb = fill
    tf = cell.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.alignment = align
    r = p.add_run(); r.text = text
    r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = color

def _title(slide, title, subtitle):
    t = slide.shapes.add_textbox(Inches(0.3), Inches(0.18), Inches(12.7), Inches(0.5))
    r = t.text_frame.paragraphs[0].add_run()
    r.text = title; r.font.size = Pt(22); r.font.bold = True; r.font.color.rgb = INK
    s = slide.shapes.add_textbox(Inches(0.3), Inches(0.72), Inches(12.7), Inches(0.4))
    rs = s.text_frame.paragraphs[0].add_run()
    rs.text = subtitle; rs.font.size = Pt(11.5); rs.font.italic = True; rs.font.color.rgb = GREY

def _takeaways(slide, x, y, w, h, head, items):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame; tf.word_wrap = True
    hp = tf.paragraphs[0]; hr = hp.add_run(); hr.text = head
    hr.font.size = Pt(13); hr.font.bold = True; hr.font.color.rgb = NAVY
    for lead, body in items:
        p = tf.add_paragraph(); p.space_before = Pt(7)
        a = p.add_run(); a.text = "▪ " + lead + "  "
        a.font.size = Pt(10.5); a.font.bold = True; a.font.color.rgb = INK
        b = p.add_run(); b.text = body
        b.font.size = Pt(10.5); b.font.color.rgb = GREY

def _footer(slide, text):
    f = slide.shapes.add_textbox(Inches(0.3), Inches(6.92), Inches(12.7), Inches(0.5))
    ff = f.text_frame; ff.word_wrap = True
    fr = ff.paragraphs[0].add_run(); fr.text = text
    fr.font.size = Pt(8.5); fr.font.italic = True; fr.font.color.rgb = GREY

def _rrect(slide, x, y, w, h, fill, line=None, line_w=1.5):
    sp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                Inches(x), Inches(y), Inches(w), Inches(h))
    sp.shadow.inherit = False                       # kill default autoshape shadow
    sp.fill.solid(); sp.fill.fore_color.rgb = fill
    if line is not None:
        sp.line.color.rgb = line; sp.line.width = Pt(line_w)
    else:
        sp.line.fill.background()
    return sp

def _panel(slide, x, y, w, h, mark, header, hdr_color, fill_color, items):
    _rrect(slide, x, y, w, h, fill_color, line=hdr_color, line_w=1.5)
    tb = slide.shapes.add_textbox(Inches(x+0.28), Inches(y+0.22), Inches(w-0.56), Inches(h-0.44))
    tf = tb.text_frame; tf.word_wrap = True
    hr = tf.paragraphs[0].add_run(); hr.text = f"{mark}  {header}"
    hr.font.size = Pt(15); hr.font.bold = True; hr.font.color.rgb = hdr_color
    for lead, body in items:
        p = tf.add_paragraph(); p.space_before = Pt(9)
        a = p.add_run(); a.text = "• " + lead + "  "
        a.font.size = Pt(11.5); a.font.bold = True; a.font.color.rgb = INK
        if body:
            b = p.add_run(); b.text = body
            b.font.size = Pt(11.5); b.font.color.rgb = GREY

# ---------------------------------------------------------------- SLIDE 1
def slide1(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _title(slide, "Cheap-Model API Baseline — Two-Benchmark Cost",
           "Full corpus · both think on/off · all variants  ·  no-tools = Batch −50% · "
           "with-tools = prompt-cache (input ×0.5, can't batch the tool loop)")

    rows = [(m, PRICE_LBL[m], sweep5_total(m), planbench_total(m)) for m in MODELS]
    HEADERS = ["Model", "$/Mtok\n(in / out)", "sweep5\nsingle-tool", "PlanBench\nfull", "Total\n/ model"]
    COL_W = [2.35, 1.30, 1.45, 1.45, 1.35]
    n_rows = len(rows) + 1
    gt = slide.shapes.add_table(n_rows, len(HEADERS), Inches(0.3), Inches(1.30),
                                Inches(sum(COL_W)), Inches(2.6)).table
    for j, w in enumerate(COL_W): gt.columns[j].width = Inches(w)
    for j, h in enumerate(HEADERS):
        _set(gt.cell(0, j), h, size=10.5, bold=True, color=WHITE,
             align=PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER, fill=NAVY)
    for i, (m, pl, s5, pb) in enumerate(rows, start=1):
        base = BAND if i % 2 == 0 else WHITE
        _set(gt.cell(i, 0), m, size=11, bold=True, fill=base)
        _set(gt.cell(i, 1), pl, size=9.5, align=PP_ALIGN.CENTER, color=GREY, fill=base)
        _set(gt.cell(i, 2), money(s5), size=10.5, align=PP_ALIGN.RIGHT, color=GREY, fill=base)
        _set(gt.cell(i, 3), money(pb), size=10.5, align=PP_ALIGN.RIGHT, color=GREY, fill=base)
        _set(gt.cell(i, 4), money(s5+pb), size=11, bold=True, align=PP_ALIGN.RIGHT, color=INK, fill=base)

    # pair table
    pairs = [("Option 1 · Haiku + Gemini Flash-Lite", ["Haiku 4.5","Gemini Flash-Lite"], True),
             ("Option 2 · Haiku + Sonnet 4.6",        ["Haiku 4.5","Sonnet 4.6"], False),
             ("+ optional · Haiku + Qwen-Flash",      ["Haiku 4.5","Qwen-Flash"], False)]
    py = 4.55
    ph = slide.shapes.add_textbox(Inches(0.3), Inches(py-0.50), Inches(8.2), Inches(0.4))
    phr = ph.text_frame.paragraphs[0].add_run(); phr.text = "Two-model pair totals (both benchmarks, discounted)"
    phr.font.size = Pt(12); phr.font.bold = True; phr.font.color.rgb = NAVY
    PW = [5.05, 1.55]
    pt = slide.shapes.add_table(len(pairs), 2, Inches(0.3), Inches(py), Inches(sum(PW)), Inches(1.4)).table
    for j, w in enumerate(PW): pt.columns[j].width = Inches(w)
    for i, (name, ms, hi) in enumerate(pairs):
        total = sum(sweep5_total(m)+planbench_total(m) for m in ms)
        fill = HILITE if hi else (BAND if i % 2 else WHITE)
        _set(pt.cell(i, 0), name, size=11, bold=hi, fill=fill)
        _set(pt.cell(i, 1), money(total), size=12, bold=True, align=PP_ALIGN.RIGHT,
             color=NAVY if hi else INK, fill=fill)

    _takeaways(slide, 8.45, 1.30, 4.6, 5.4, "Why option 1", [
        ("Both are closed frontier models.", "You can't self-host Haiku or Gemini — that's "
         "exactly what API budget should buy. ~$1,047 for BOTH full benchmarks, 2 models."),
        ("Sonnet is the pricier anchor.", "Option 2 = $3,253 (3×). Sonnet isn't 'small' — it "
         "buys a stronger upper-bound point, not a cheap one."),
        ("Qwen-Flash is cheapest but redundant.", "+$59/model and matches the tested family, "
         "but you already run Qwen locally for free on SLURM, and API-Qwen ≠ your checkpoint "
         "(different corpus). Use only as a managed point."),
        ("Levers save ~30%, not more.", "Output (priced 5× input) is untouched by caching, and "
         "the with-tools arm can't batch. List → discounted: Sonnet $3,735 → $2,440."),
    ])
    _footer(slide, "Tokens: measured Qwen3.5-9B (real for Qwen, PROXY for closed models — "
            "extended-thinking output may be 2-5× on think-on cells). PlanBench tokens = aggregate proxy. "
            "Pricing: Claude authoritative; Gemini/Qwen web, Jun 2026. Pilot ~$20-35 to calibrate before committing.")

# ---------------------------------------------------------------- SLIDE 2
def slide2(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _title(slide, "Single-Tool (sweep5) — Cost by Task",
           "Per-model task TOTAL across full matrix (no-tools 3 variants + with-tools 6 variants, "
           "× 2 think) · tokens are cumulative across the agent loop")

    HEADERS = ["Task", "trials\n/model", "in tok\n/trial", "out tok\n/trial",
               "Haiku\n$", "Gemini\n$", "Sonnet\n$", "Qwen\n$"]
    COL_W = [2.35, 1.05, 1.05, 1.05, 1.05, 1.05, 1.05, 1.0]
    order = ["solve","validate_domain","validate_problem","validate_plan","simulate"]
    n_rows = len(order) + 2  # +header +total
    gt = slide.shapes.add_table(n_rows, len(HEADERS), Inches(0.3), Inches(1.30),
                                Inches(sum(COL_W)), Inches(3.2)).table
    for j, w in enumerate(COL_W): gt.columns[j].width = Inches(w)
    for j, h in enumerate(HEADERS):
        _set(gt.cell(0, j), h, size=10, bold=True, color=WHITE,
             align=PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER, fill=NAVY)
    tt = {m: sweep5_task_totals(m) for m in MODELS}
    for i, task in enumerate(order, start=1):
        ntok, ai, ao = task_token_means(task)
        dom = (task == "validate_plan")
        base = HILITE if dom else (BAND if i % 2 == 0 else WHITE)
        _set(gt.cell(i, 0), TASK_LABEL[task], size=10.5, bold=dom, color=RED if dom else INK, fill=base)
        _set(gt.cell(i, 1), f"{ntok:,}", size=10, align=PP_ALIGN.RIGHT, color=GREY, fill=base)
        _set(gt.cell(i, 2), f"{ai:,.0f}", size=10, align=PP_ALIGN.RIGHT, color=GREY, fill=base)
        _set(gt.cell(i, 3), f"{ao:,.0f}", size=10, align=PP_ALIGN.RIGHT, color=GREY, fill=base)
        for k, m in enumerate(["Haiku 4.5","Gemini Flash-Lite","Sonnet 4.6","Qwen-Flash"]):
            _set(gt.cell(i, 4+k), money(tt[m][task]), size=10, bold=dom,
                 align=PP_ALIGN.RIGHT, color=INK, fill=base)
    # total row
    r = len(order) + 1
    _set(gt.cell(r, 0), "ALL TASKS", size=10.5, bold=True, color=WHITE, fill=NAVY)
    _set(gt.cell(r, 1), "27,360", size=10, bold=True, align=PP_ALIGN.RIGHT, color=WHITE, fill=NAVY)
    _set(gt.cell(r, 2), "", size=10, fill=NAVY); _set(gt.cell(r, 3), "", size=10, fill=NAVY)
    for k, m in enumerate(["Haiku 4.5","Gemini Flash-Lite","Sonnet 4.6","Qwen-Flash"]):
        _set(gt.cell(r, 4+k), money(sweep5_total(m)), size=10.5, bold=True,
             align=PP_ALIGN.RIGHT, color=WHITE, fill=NAVY)

    _takeaways(slide, 0.3, 4.85, 12.7, 2.0, "Read this table", [
        ("validate_plan = 66% of every bill.", "It runs 10 plan fixtures (b1-b5 buggy + v1-v5 valid) "
         "× 100 problems × variants × think = 18,000 of 27,360 trials. The #1 cut target (slide 3)."),
        ("with-tools input dwarfs no-tools.", "solve/simulate carry 11-17K input tok/trial — the tool "
         "loop re-bills domain+schemas+history each turn; caching that prefix is the main input lever."),
        ("$/trial = task $ ÷ trials.", "e.g. validate_plan on Gemini = $79/18,000 ≈ $0.004/prompt; "
         "on Sonnet ≈ $0.046; on Qwen ≈ $0.001."),
    ])
    _footer(slide, "Discounted (no-tools Batch −50%; with-tools input-cache ×0.5). Per-task token means "
            "averaged over the task's 4 cells weighted by trial count. Source: sweep5v2 Qwen3.5-9B corpus.")

# ---------------------------------------------------------------- SLIDE 3
def slide3(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _title(slide, "Cutting Cost by Cutting Volume",
           "% reductions are model-independent (token structure is fixed) — they transfer to any pair. "
           "$ shown for the recommended Haiku + Gemini Flash-Lite pair (sweep5)")

    pair = ["Haiku 4.5", "Gemini Flash-Lite"]
    base = sum(sweep5_scaled(m) for m in pair)
    scen = [
        ("FULL (baseline)", dict(), "all 5 tasks · 20 domains · 6+3 variants · both think", False),
        ("validate_plan 10→4 fixtures", dict(vp_fix=4), "drop redundant plan fixtures", False),
        ("with-tools variants 6→2", dict(wt_var=2), "fewer prompt phrasings", False),
        ("domains 20→10 (half pool)", dict(dom_frac=0.5), "halve the domain pool", False),
        ("no-tools variants 3→1", dict(nt_var=1), "small — no-tools is cheap", False),
        ("think-off only", dict(think_both=False), "biggest single lever", False),
        ("LEAN  (vp4 · ½dom · wt2 · nt1)", dict(vp_fix=4, dom_frac=0.5, wt_var=2, nt_var=1),
         "stack structural cuts, keep both think", True),
        ("LEAN + think-off", dict(vp_fix=4, dom_frac=0.5, wt_var=2, nt_var=1, think_both=False),
         "floor — power drops", False),
    ]
    HEADERS = ["Scenario", "% of full", "Haiku+Gemini $", "Lever"]
    COL_W = [3.45, 1.25, 1.75, 4.55]
    gt = slide.shapes.add_table(len(scen)+1, len(HEADERS), Inches(0.3), Inches(1.35),
                                Inches(sum(COL_W)), Inches(3.7)).table
    for j, w in enumerate(COL_W): gt.columns[j].width = Inches(w)
    for j, h in enumerate(HEADERS):
        _set(gt.cell(0, j), h, size=10.5, bold=True, color=WHITE,
             align=PP_ALIGN.LEFT if j in (0, 3) else PP_ALIGN.CENTER, fill=NAVY)
    for i, (name, kw, lever, hi) in enumerate(scen, start=1):
        val = sum(sweep5_scaled(m, **kw) for m in pair)
        pct = val / base * 100
        fill = HILITE if hi else (BAND if i % 2 == 0 else WHITE)
        _set(gt.cell(i, 0), name, size=10.5, bold=(i == 1 or hi), fill=fill)
        _set(gt.cell(i, 1), f"{pct:.0f}%", size=11, bold=True, align=PP_ALIGN.CENTER,
             color=NAVY if hi else INK, fill=fill)
        _set(gt.cell(i, 2), money(val), size=10.5, align=PP_ALIGN.RIGHT, color=INK, fill=fill)
        _set(gt.cell(i, 3), lever, size=9.5, color=GREY, fill=fill)

    _takeaways(slide, 0.3, 5.35, 12.7, 1.5, "Biggest levers, in order", [
        ("Drop think-on: −64%.", "Halves the matrix and removes the extended-thinking output blow-up "
         "(the single biggest closed-model cost risk)."),
        ("Trim with-tools variants 6→2: −52% · halve domains: −50% · validate_plan 10→4: −40%.",
         "These stack: keeping both think but cutting structure → ~10% of full (Haiku+Gemini "
         "sweep5 $537 → ~$54), with statistical power largely intact."),
    ])
    _footer(slide, "Scenarios computed on the sweep5 token table. PlanBench scales the same way "
            "(its analogue of validate_plan-style cost is the with-tools think-on cell). Cuts are "
            "labeled variants — flag any domain/fixture sampling in the writeup.")

# ---------------------------------------------------------------- SLIDE 4
def slide4(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _title(slide, "What We Cut vs What Stays Solid",
           "Rule of thumb: cut the repeats, keep the spread.  The cuts only remove spares — "
           "the comparison stays intact.")
    GREEN_H = RGBColor(0x3E, 0x82, 0x3C); GREEN_F = RGBColor(0xEC, 0xF6, 0xEC)
    AMBER_H = RGBColor(0xAE, 0x70, 0x1C); AMBER_F = RGBColor(0xFB, 0xF1, 0xDE)

    _panel(slide, 0.3, 1.45, 6.25, 4.05, "✓", "KEEP — this IS the experiment",
           GREEN_H, GREEN_F, [
        ("Tools vs no-tools.", "the whole question — drop it and there's no experiment."),
        ("Both world-families.", "keep some classical AND some numeric, or you can't claim it generalizes."),
        ("Both think on / off (ideally).", "a real research question, and only a 2× cost."),
        ("Hundreds of answers per cell.", "enough for honest confidence bars (Wilson CIs)."),
    ])
    _panel(slide, 6.8, 1.45, 6.23, 4.05, "✂", "SAFE TO CUT — just repeats",
           AMBER_H, AMBER_F, [
        ("Wordings 6 → 2.", "keep 2 phrasings; still shows wording doesn't change the result.   ‒52%"),
        ("Plan-checks 10 → 4.", "2 broken + 2 good; still tests both skills.   −40%"),
        ("Worlds 20 → 10.", "keep 5 classical + 5 numeric (balanced).   −50%"),
        ("Drop think-on.", "the single biggest lever.   −64%"),
    ])

    # recipe band
    _rrect(slide, 0.3, 5.78, 12.73, 0.92, NAVY)
    tb = slide.shapes.add_textbox(Inches(0.55), Inches(5.90), Inches(12.3), Inches(0.7))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]
    a = p.add_run(); a.text = "Lean-but-solid recipe:  "
    a.font.size = Pt(12.5); a.font.bold = True; a.font.color.rgb = WHITE
    b = p.add_run()
    b.text = ("both models · tools + no-tools · both think · 10 balanced worlds · "
              "2 wordings · 4 plan-checks   →   ~10% of full  (~$54 sweep5, Haiku+Gemini), "
              "still with real confidence bars.")
    b.font.size = Pt(12.5); b.font.color.rgb = RGBColor(0xDD, 0xE6, 0xF2)

    _footer(slide, "Cuts are labeled variants — flag any domain/fixture sampling in the writeup. "
            "% reductions are model-independent; $ shown for the recommended cheap pair.")

# ---------------------------------------------------------------- SLIDE 5
def slide5(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _title(slide, "Alternative — Rent One Steady GPU, Self-Host the Open Roster",
           "Run the OPEN models (Qwen3.5-0.8/4/9B · Qwen3.6-35B · maybe gemma4-31B) on a persistent "
           "neocloud box, not the queued 3090/RTX-6000 cluster. Different models & purpose from the "
           "API closed-model baseline above — this is the actual experiment roster.")
    GREEN = RGBColor(0x3E, 0x82, 0x3C)

    # ---- route comparison (full width) ----
    api_pair = sum(sweep5_total(m) + planbench_total(m) for m in ["Haiku 4.5", "Gemini Flash-Lite"])
    h2lo, h2hi = gpu_band("H200-141GB"); h1lo, h1hi = gpu_band("H100-80GB")
    ROUTES = [
        ("Free SLURM cluster (3090/RTX-6000)", "$0", "queued", "✗ can't seat", "shared, mixed configs", False),
        ("Rented H200-141GB", money_band(h2lo, h2hi), "yes", "✓ clean BF16", "one vanilla vLLM · no TP/FP8", True),
        ("Rented H100-80GB (budget)", money_band(h1lo, h1hi), "yes", "FP8 / TP=2", "one vLLM · more moving parts", False),
        ("API closed models (slides 1-4)", money(api_pair), "yes", "n/a (closed)", "OpenAI API · by-the-token", False),
    ]
    RH = ["Route", "GPU/API $", "Steady?", "35B in BF16", "Backend / moving parts"]
    RW = [3.55, 1.55, 1.25, 1.55, 4.8]
    rt = slide.shapes.add_table(len(ROUTES) + 1, len(RH), Inches(0.3), Inches(1.28),
                                Inches(sum(RW)), Inches(1.95)).table
    for j, w in enumerate(RW): rt.columns[j].width = Inches(w)
    for j, h in enumerate(RH):
        _set(rt.cell(0, j), h, size=10, bold=True, color=WHITE,
             align=PP_ALIGN.LEFT if j in (0, 4) else PP_ALIGN.CENTER, fill=NAVY)
    for i, (name, cost_s, steady, bf16, backend, hi) in enumerate(ROUTES, start=1):
        fill = HILITE if hi else (BAND if i % 2 == 0 else WHITE)
        _set(rt.cell(i, 0), name, size=10, bold=hi, fill=fill)
        _set(rt.cell(i, 1), cost_s, size=10, bold=hi, align=PP_ALIGN.CENTER,
             color=NAVY if hi else INK, fill=fill)
        _set(rt.cell(i, 2), steady, size=10, align=PP_ALIGN.CENTER, color=GREY, fill=fill)
        _set(rt.cell(i, 3), bf16, size=10, align=PP_ALIGN.CENTER,
             color=RED if bf16.startswith("✗") else (NAVY if hi else GREY), fill=fill)
        _set(rt.cell(i, 4), backend, size=9.5, color=GREY, fill=fill)

    # ---- per-model fit (left) ----
    cap = slide.shapes.add_textbox(Inches(0.3), Inches(3.42), Inches(5.7), Inches(0.32))
    cr = cap.text_frame.paragraphs[0].add_run()
    cr.text = "Per-model BF16 fit (served one at a time)"
    cr.font.size = Pt(12); cr.font.bold = True; cr.font.color.rgb = NAVY
    rh = ["Open model", "BF16 GB", "H200-141", "H100-80"]
    rw = [1.95, 1.05, 1.3, 1.4]
    rost = slide.shapes.add_table(len(ROSTER) + 1, len(rh), Inches(0.3), Inches(3.78),
                                  Inches(sum(rw)), Inches(2.05)).table
    for j, w in enumerate(rw): rost.columns[j].width = Inches(w)
    for j, h in enumerate(rh):
        _set(rost.cell(0, j), h, size=9.5, bold=True, color=WHITE,
             align=PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER, fill=NAVY)
    for i, (m, gb) in enumerate(ROSTER, start=1):
        big = gb > 60
        base = BAND if i % 2 == 0 else WHITE
        _set(rost.cell(i, 0), m, size=9.5, fill=base)
        _set(rost.cell(i, 1), f"{gb:.0f}" if gb >= 10 else f"{gb:.1f}", size=9.5,
             align=PP_ALIGN.RIGHT, color=GREY, fill=base)
        _set(rost.cell(i, 2), "✓", size=9.5, align=PP_ALIGN.CENTER, color=GREEN, fill=base)
        _set(rost.cell(i, 3), "FP8/TP2" if big else "✓", size=9, align=PP_ALIGN.CENTER,
             color=RED if big else GREEN, fill=base)

    # ---- decision & constraints (right) ----
    _takeaways(slide, 6.2, 3.42, 6.83, 3.4, "Decision & constraints", [
        ("H200-141GB — fewest moving parts.", "every model in clean BF16 on a single GPU: no "
         "tensor-parallel, no FP8. H100-80 only if budget bites (forces FP8/TP=2 on the 31-35B)."),
        ("Time-share one box.", "load a model → run its sweep5v2 + PlanBench cells → swap. Vanilla "
         "vLLM OpenAI server; ~40-50 GPU-hrs @ ~$3/hr ≈ $120-150 for all five (PlanBench extra, TBD)."),
        ("Harness change is tiny.", "VLLMClient is OpenAI-compatible — only base_url + key move to "
         "the rented box. Per-model flags: --max-model-len, --gpu-memory-utilization, --served-model-name."),
        ("Corpus isolation is load-bearing.", "each model's trials.jsonl from ONE backend; keep "
         "temp/top_p/max_tokens/seed identical to cluster cells. Never split a model across cluster + rental."),
    ])

    _footer(slide, "Cost & GPU-hours are ESTIMATES from the deployment handoff (~40-50 GPU-hrs @ "
            "~$3/hr H200); confirm with a short pilot before the full sweep. † gemma4-31B optional. "
            "Open items for the planner: PlanBench trial/problem count · H200 vs H100+FP8 · whether the "
            "0.8-9B cells stay on the free cluster (cheaper) or move to the box (one backend).")

# ---------------------------------------------------------------- build
def build():
    prs = Presentation()
    prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
    slide1(prs); slide2(prs); slide3(prs); slide4(prs); slide5(prs)
    out = Path(__file__).resolve().parent / "cheap_model_cost_slides.pptx"
    prs.save(str(out))
    print(f"wrote {out}  ({len(prs.slides)} slides)")

    # echo the headline numbers for verification
    print("\n-- per-model (discounted) --")
    for m in MODELS:
        s5, pb = sweep5_total(m), planbench_total(m)
        print(f"  {m:18} sweep5={money(s5):>7}  planbench={money(pb):>7}  total={money(s5+pb):>7}")
    print("-- pairs --")
    for name, ms in [("Haiku+Gemini",["Haiku 4.5","Gemini Flash-Lite"]),
                     ("Haiku+Sonnet",["Haiku 4.5","Sonnet 4.6"]),
                     ("Haiku+Qwen",["Haiku 4.5","Qwen-Flash"])]:
        print(f"  {name:14} {money(sum(sweep5_total(m)+planbench_total(m) for m in ms))}")
    print("-- rented-GPU alternative (open roster, sweep5v2; PlanBench extra) --")
    for g in GPU:
        lo, hi = gpu_band(g)
        print(f"  {g:14} {money_band(lo,hi):>12}  ({GPU[g][0]:.2f}/hr x {GPU_HRS[0]}-{GPU_HRS[1]} GPU-hr) — {GPU[g][1]}")


if __name__ == "__main__":
    build()
