"""Build editable project slides and submission reports from the latest completed demo runs."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches as DInches, Pt as DPt, RGBColor as DRGB
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "backend"))
load_dotenv(ROOT / ".env")

from healthcare_gis.common import clean
from healthcare_gis.database import connect

OUT = Path(__file__).resolve().parent
NAVY, TEAL, MINT = "102A43", "087E8B", "D9F3EE"
SKY, GOLD, CORAL, WHITE = "EAF2F8", "F2B544", "D66A5C", "FFFFFF"
INK, GREY, PALE, GREEN = "203247", "627D98", "F5F8FA", "2F855A"
TITLE = "Healthcare Atlas"
SUBTITLE = (
    "GIS and AI decision support for healthcare accessibility "
    "and future hospital planning"
)


def evidence():
    client, db = connect()
    try:
        kinds = ("accessibility", "train", "predict", "candidates", "optimization")
        runs = {
            kind: db.analysis_runs.find_one(
                {"analysis_type": kind, "status": "COMPLETED"},
                sort=[("created_at", -1)],
            )
            for kind in kinds
        }
        if any(run is None for run in runs.values()):
            raise RuntimeError(
                "Missing completed workflow stages; refusing to create an "
                "incomplete submission pack."
            )
        results = {kind: clean(run.get("result", {})) for kind, run in runs.items()}
        if not results["train"].get("synthetic") or not results["predict"].get(
            "synthetic"
        ):
            raise RuntimeError("Expected explicitly synthetic workflow results.")
        counts = {
            name: db[name].count_documents({})
            for name in (
                "hospitals",
                "population_areas",
                "roads",
                "boundaries",
                "healthcare_demand",
            )
        }
        return results, counts
    finally:
        client.close()


R, COUNTS = evidence()
A, T, P, C, O = (R[k] for k in ("accessibility", "train", "predict", "candidates", "optimization"))
BEFORE, AFTER = O["before"], O["after"]
COMPARISON = T.get("comparison", {})
MODELS = [
    ("Linear regression", COMPARISON.get("linear_regression", {}).get("test", {})),
    ("Random forest", COMPARISON.get("random_forest", {}).get("test", {})),
    ("XGBoost", COMPARISON.get("xgboost", {}).get("test", {})),
]
DATE = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %B %Y")
SECTIONS = [
    (
        "Executive Summary",
        [
            "Healthcare Atlas is a local-first web decision-support prototype linking GIS accessibility analysis, demand forecasting, candidate-site screening and multi-objective hospital-location optimization. The system combines an Angular/Leaflet frontend, FastAPI application API, separate Python ML service, and MongoDB GeoJSON storage.",
            f"The demonstration uses a fully synthetic study area near Chennai, Tamil Nadu: {COUNTS['population_areas']} fictional zones, {COUNTS['hospitals']} synthetic hospitals, {COUNTS['roads']} road features, {COUNTS['boundaries']} boundary records, and {COUNTS['healthcare_demand']} annual demand records. The workflow completed end-to-end on {DATE}.",
            f"In the three-hospital scenario, modeled mean travel time changed from {BEFORE['averageTravelTimeMinutes']:.2f} to {AFTER['averageTravelTimeMinutes']:.2f} minutes and the mean accessibility index changed from {BEFORE['meanAccessibilityIndex']:.3f} to {AFTER['meanAccessibilityIndex']:.3f}. These are results on synthetic inputs only—not observed impacts, statewide estimates, or evidence of real-world model accuracy.",
        ],
    ),
    (
        "1. Introduction and Problem Statement",
        [
            "Healthcare access is shaped by the spatial distribution of population and facilities, road-network connectivity, travel time, capacity, and emergency-service availability. Facility counts alone cannot describe how access varies across communities or how alternative locations may change travel burdens.",
            "This project integrates spatial data management and analysis with demand modeling and location optimization. It is intended to support exploration and comparison by analysts and planners—not to make autonomous siting or clinical decisions.",
        ],
    ),
    (
        "2. Aim and Objectives",
        [
            "Aim: demonstrate an auditable GIS and AI workflow for measuring healthcare accessibility and exploring future hospital locations.",
            "Objectives: manage hospital, population, road, boundary, and demand layers; compute configurable distance- and road-based accessibility measures; train and evaluate demand models with chronological splits; forecast demand; screen candidate locations by population, demand, road access, separation, and land-use rules; optimize proposed sites and compare modeled before/after results; and provide interactive maps, analysis history, and exports.",
        ],
    ),
    (
        "3. Scope and Dataset",
        [
            f"The live demonstration is small and synthetic. It contains {COUNTS['population_areas']} fictional zones around Chennai, {COUNTS['hospitals']} synthetic existing facilities, {COUNTS['roads']} synthetic road features, {COUNTS['boundaries']} boundary/land-use records, and {COUNTS['healthcare_demand']} historical demand entries for 2012–2025. The modeled population totals {A['population']:,}.",
            "This dataset is not official Tamil Nadu administrative geography and does not represent all of Tamil Nadu. Coordinates, facilities, demographics, demand, land-use boundaries, and road speeds are constructed for demonstration. No patient-level records are used. These outputs must not be cited as observed local evidence.",
        ],
    ),
    (
        "4. System Architecture",
        [
            "The Angular/TypeScript client presents dashboards, maps, and workflow controls. The FastAPI business API owns authentication, authorization, validation, data access, audit logging, and job lifecycle. MongoDB stores application records, GeoJSON layers, workflow runs, and results. A separate FastAPI ML service performs training, prediction, and genetic-algorithm optimization. The browser does not access MongoDB directly.",
            "Long-running operations are persisted as QUEUED, RUNNING, COMPLETED, FAILED, or CANCELLED jobs. MongoDB 2dsphere indexes support spatial queries; road travel times use a graph built from road features.",
        ],
    ),
    (
        "5. Methodology",
        [
            "Accessibility: estimate distance or road-network travel time from each population zone to facilities; combine distance, travel time, capacity, and emergency availability with configurable weights; and summarize threshold coverage and underserved population. Unreachable routes remain explicit; a documented penalty is applied only inside optimizer fitness.",
            "Demand modeling: build lagged area/year rows using previous-period demand and demographic/spatial features. Split years chronologically: train 2013–2019, validate 2020–2022, and test 2023–2025. Compare linear regression, random forest, and XGBoost; select by validation RMSE; then recursively forecast 2027.",
            "Candidate generation: evaluate grid points using population and predicted-demand thresholds, separation from existing hospitals, road access, study-boundary inclusion, and water/protected-area exclusions. Without parcel prices, sites receive equal relative assumed cost—not actual budget estimates.",
            "Optimization: a genetic algorithm selects the requested number of candidates using weighted population coverage, demand coverage, accessibility improvement, road access, and cost. The system recalculates access after adding proposed facilities and reports recommendations and before/after measures. It does not guarantee a global optimum.",
        ],
    ),
    (
        "6. Results",
        [
            f"Baseline accessibility: {A['population']:,} synthetic residents; {A['coveragePercent']:.1f}% within the configured 30-minute threshold; mean travel time {A['averageTravelTimeMinutes']:.2f} minutes; underserved population {A['underservedPopulation']:,}; mean accessibility index {A['meanAccessibilityIndex']:.3f}. Distribution: {A['distribution'].get('Good', 0)} Good, {A['distribution'].get('Moderate', 0)} Moderate, {A['distribution'].get('Poor', 0)} Poor, and {A['distribution'].get('Critical', 0)} Critical zones.",
            f"Model comparison: {T.get('records')} lagged rows; {T.get('algorithm')} selected by validation RMSE. Held-out synthetic-test metrics: MAE {T['metrics']['mae']:.2f}, RMSE {T['metrics']['rmse']:.2f}, R² {T['metrics']['r2']:.3f}, MAPE {T['metrics']['mape']:.2f}%. These describe generated data only.",
            f"Forecast and candidate sites: the 2027 forecast estimated {P['totalPredictedDemand']:,.0f} synthetic demand units across {P['areas']} zones. Candidate generation returned {C['count']} feasible points. Points are not surveyed or verified parcels.",
            f"Three-hospital scenario: mean travel time changed from {BEFORE['averageTravelTimeMinutes']:.2f} to {AFTER['averageTravelTimeMinutes']:.2f} minutes, a {(BEFORE['averageTravelTimeMinutes']-AFTER['averageTravelTimeMinutes'])/BEFORE['averageTravelTimeMinutes']*100:.1f}% modeled reduction. Mean index changed from {BEFORE['meanAccessibilityIndex']:.3f} to {AFTER['meanAccessibilityIndex']:.3f}. Coverage remained {BEFORE['coveragePercent']:.1f}% at 30 minutes; the demo therefore shows a change in mean time/index, not threshold coverage. Relative cost is {O['estimatedCostUnits']:.0f} assumed units, at equal cost per proposed site.",
        ],
    ),
    (
        "7. Results Tables",
        [
            "Tables compare the existing synthetic baseline with the three-site scenario and report the held-out temporal model comparison. Synthetic results are for software demonstration only.",
        ],
    ),
    (
        "8. Implementation and Validation",
        [
            "During preparation, the frontend production build succeeded and all three frontend tests passed. Frontend, API, and ML health endpoints responded successfully. Authenticated API checks confirmed synthetic data load, completion of each workflow stage, persistence of analysis history, and successful PDF export.",
            "The local stack consists of the Angular development server, FastAPI API, ML service, and MongoDB. Browser end-to-end automation was not run as part of this report-preparation validation.",
        ],
    ),
    (
        "9. Limitations and Responsible Use",
        [
            "All measured values come from deterministic synthetic data. Strong test metrics do not establish performance on real populations. The 100% baseline threshold coverage reflects this small connected synthetic geography and configured threshold; it is not a Tamil Nadu access estimate.",
            "Synthetic roads and travel assumptions omit actual traffic, public transport, seasonal access, patient choice, and referral patterns. Demand is not a clinical workload estimate. Equal site costs omit acquisition and development costs. Geometric inclusion does not establish ownership, zoning, environmental clearance, engineering suitability, community acceptance, or operational viability.",
            "The optimizer is heuristic and does not prove global optimality. Real use requires licensed current aggregate data, independent data-quality review, geographic and temporal external validation, fairness and uncertainty assessment, security/privacy review, and multidisciplinary participation. Avoid patient-level personal information.",
        ],
    ),
    (
        "10. Future Work",
        [
            "Replace synthetic layers with licensed and quality-checked Tamil Nadu datasets: official boundaries, population projections, validated facility attributes, realistic road/travel conditions, and documented demand sources. Add spatial and temporal external validation, uncertainty intervals, and fairness analysis. Incorporate verified parcel, land-use, environmental, and cost data; compare objective weights and robust scenarios; expand browser-based end-to-end tests and deployment monitoring.",
        ],
    ),
    (
        "11. Conclusion",
        [
            "Healthcare Atlas demonstrates a complete software workflow connecting GIS data, accessibility analysis, synthetic demand forecasting, candidate-site screening, multi-objective optimization, map review, and reporting. The prototype is suitable for demonstrating system behavior and methodology; it is not a validated planning recommendation for Chennai or Tamil Nadu. Practical conclusions require real validated data and multidisciplinary review.",
        ],
    ),
    (
        "References and Project Materials",
        [
            "Internal project materials: doc/01-REQUIREMENTS.md; doc/02-ARCHITECTURE.md; doc/07-FRONTEND.md; doc/08-BACKEND.md; doc/10-EVALUATION.md; doc/11-SECURITY.md; README.md. Metrics were read from persisted completed synthetic workflow records on "
            + DATE
            + ". No external population, hospital, road, or demand source was used for demo outputs.",
        ],
    ),
]


def ppt_color(hex_color):
    return RGBColor.from_string(hex_color)


def ppt_box(slide, x, y, w, h, text, size=14, color=INK, bold=False, align=PP_ALIGN.LEFT):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = Inches(0.06)
    frame.margin_right = Inches(0.06)
    frame.margin_top = Inches(0.04)
    frame.margin_bottom = Inches(0.04)
    para = frame.paragraphs[0]
    para.alignment = align
    run = para.add_run()
    run.text = str(text)
    run.font.name = "Aptos"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = ppt_color(color)
    return shape


def ppt_rect(slide, x, y, w, h, fill, rounded=True, outline=None):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = ppt_color(fill)
    if outline:
        shape.line.color.rgb = ppt_color(outline)
    else:
        shape.line.fill.background()
    return shape


def slide_base(prs, title):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = ppt_color(PALE)
    ppt_rect(slide, 0, 0, 13.33, 0.14, TEAL, False)
    ppt_box(slide, 0.55, 0.31, 12, 0.27, "HEALTHCARE ATLAS · PROJECT EXPLAINER", 9, TEAL, True)
    ppt_box(slide, 0.55, 0.68, 12.2, 0.6, title, 26, NAVY, True)
    ppt_rect(slide, 0.55, 7.11, 12.2, 0.015, "CBD5E0", False)
    ppt_box(slide, 0.58, 7.16, 10.8, 0.18, "SYNTHETIC CHENNAI-AREA STUDY · NOT STATEWIDE OR OBSERVED HEALTH DATA", 7, GREY)
    ppt_box(slide, 12.15, 7.14, 0.5, 0.2, str(len(prs.slides)).zfill(2), 9, TEAL, True, PP_ALIGN.RIGHT)
    return slide


def ppt_card(slide, x, y, w, label, value, sub, accent=TEAL):
    ppt_rect(slide, x, y, w, 1.55, WHITE, outline="D9E2EC")
    ppt_rect(slide, x, y, 0.07, 1.55, accent, False)
    ppt_box(slide, x + 0.18, y + 0.16, w - 0.3, 0.26, label.upper(), 9, GREY, True)
    ppt_box(slide, x + 0.18, y + 0.52, w - 0.3, 0.5, value, 23, NAVY, True)
    ppt_box(slide, x + 0.18, y + 1.1, w - 0.3, 0.32, sub, 9, GREY)


def create_ppt():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.33), Inches(7.5)
    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = ppt_color(NAVY)
    ppt_rect(s, 0.75, 0.8, 0.17, 5.85, TEAL, False)
    ppt_box(s, 1.25, 1.05, 10.7, 0.35, f"PROJECT PRESENTATION | {DATE.upper()}", 11, "79D4C7", True)
    ppt_box(s, 1.2, 1.8, 10.8, 1.1, TITLE, 38, WHITE, True)
    ppt_box(s, 1.25, 3.05, 10.6, 1.1, SUBTITLE, 23, "DCE7EF")
    ppt_rect(s, 1.28, 4.62, 8.65, 0.66, "193B55")
    ppt_box(s, 1.48, 4.79, 8.2, 0.3, "DEMO SCOPE: fictional districts near Chennai, Tamil Nadu", 14, "FFE0A3", True)
    ppt_box(s, 1.3, 6.25, 10.5, 0.35, "Submitted by: ____________________  |  Institution: ____________________", 12, "DCE7EF")
    ppt_box(s, 11.55, 6.75, 1, 0.24, "01", 11, "79D4C7", True, PP_ALIGN.RIGHT)

    s = slide_base(prs, "The planning challenge")
    ppt_box(s, 0.75, 1.55, 5.1, 0.5, "Access is a network + geography problem", 20, NAVY, True)
    for i, text in enumerate(
        (
            "Facility counts do not describe who can reach care.",
            "Travel time, capacity, and emergency service affect access.",
            "Planners need transparent comparisons of future locations.",
        )
    ):
        y = 2.25 + i * 0.9
        ppt_rect(s, 0.82, y + 0.12, 0.12, 0.12, TEAL)
        ppt_box(s, 1.08, y, 4.8, 0.68, text, 15)
    ppt_rect(s, 6.35, 1.65, 6.25, 4.7, NAVY)
    ppt_box(s, 6.75, 2.03, 5.4, 0.3, "PROJECT RESPONSE", 11, "79D4C7", True)
    ppt_box(s, 6.75, 2.6, 5.2, 1.05, "Turn spatial data into an explainable planning workflow.", 24, WHITE, True)
    ppt_box(s, 6.77, 4.08, 5.1, 1.1, "Measure access  →  forecast demand  →  screen sites  →  compare scenarios", 16, "DCE7EF")
    ppt_box(s, 6.78, 5.78, 5.3, 0.35, "Decision support; human review remains essential.", 11, "FFE0A3", True)

    s = slide_base(prs, "Project objectives and user value")
    objectives = [
        ("01", "Measure", "Road travel time and a configurable accessibility index."),
        ("02", "Forecast", "Compare demand models with chronological splits."),
        ("03", "Screen", "Apply access, separation, and land constraints."),
        ("04", "Compare", "Optimize sites and quantify before/after changes."),
    ]
    for i, (n, head, body) in enumerate(objectives):
        x, y = 0.7 + (i % 2) * 6.1, 1.62 + (i // 2) * 2.35
        ppt_rect(s, x, y, 5.72, 1.9, WHITE, outline="D9E2EC")
        ppt_rect(s, x + 0.2, y + 0.23, 0.62, 0.62, TEAL)
        ppt_box(s, x + 0.25, y + 0.36, 0.5, 0.24, n, 12, WHITE, True, PP_ALIGN.CENTER)
        ppt_box(s, x + 1.02, y + 0.27, 4.3, 0.35, head, 18, NAVY, True)
        ppt_box(s, x + 1.02, y + 0.82, 4.35, 0.72, body, 12, GREY)

    s = slide_base(prs, "System architecture")
    blocks = [
        (0.75, 2.0, "Angular + Leaflet", "Dashboard · maps · workflow", TEAL),
        (4.0, 2.0, "FastAPI backend", "Auth · API · job queue", NAVY),
        (7.25, 2.0, "MongoDB GeoJSON", "Records · runs · indexes", GREEN),
        (10.15, 4.25, "ML service", "Train · predict · optimize", CORAL),
    ]
    for x, y, head, body, color in blocks:
        ppt_rect(s, x, y, 2.45, 1.35, WHITE, outline="D9E2EC")
        ppt_rect(s, x, y, 2.45, 0.1, color, False)
        ppt_box(s, x + 0.15, y + 0.32, 2.15, 0.32, head, 14, NAVY, True)
        ppt_box(s, x + 0.15, y + 0.78, 2.16, 0.42, body, 10, GREY)
    for x1, y1, x2, y2 in ((3.2, 2.68, 4.0, 2.68), (6.45, 2.68, 7.25, 2.68), (6.4, 3.15, 10.15, 4.65)):
        line = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
        line.line.color.rgb = ppt_color(TEAL)
        line.line.width = Pt(2)
        line.line.end_arrowhead = True
    ppt_rect(s, 0.9, 4.42, 8.5, 1.15, SKY)
    ppt_box(s, 1.15, 4.65, 8, 0.3, "Asynchronous workflow", 13, NAVY, True)
    ppt_box(s, 1.15, 5.07, 8, 0.34, "QUEUED → RUNNING → COMPLETED / FAILED / CANCELLED", 11, GREY)
    ppt_box(s, 0.95, 6.06, 11.4, 0.45, "Spatial data and job results flow through the API; the browser never accesses MongoDB directly.", 11)

    s = slide_base(prs, "End-to-end methodology")
    steps = [
        ("1", "Prepare", "Zones, facilities, roads, boundaries, demand"),
        ("2", "Measure", "Travel time + population/capacity/emergency"),
        ("3", "Learn", "Temporal split; compare three models"),
        ("4", "Generate", "Forecast → constraints → candidate points"),
        ("5", "Optimize", "Select sites; recompute access"),
    ]
    for i, (n, head, body) in enumerate(steps):
        x = 0.55 + i * 2.58
        ppt_rect(s, x, 2.15, 2.3, 2.45, WHITE, outline="D9E2EC")
        ppt_rect(s, x + 0.16, 2.38, 0.52, 0.52, TEAL)
        ppt_box(s, x + 0.2, 2.48, 0.44, 0.22, n, 13, WHITE, True, PP_ALIGN.CENTER)
        ppt_box(s, x + 0.16, 3.12, 2, 0.32, head, 15, NAVY, True)
        ppt_box(s, x + 0.16, 3.62, 1.98, 0.78, body, 11, GREY)
        if i < 4:
            line = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x + 2.3), Inches(3.35), Inches(x + 2.55), Inches(3.35))
            line.line.color.rgb = ppt_color(GOLD)
            line.line.end_arrowhead = True
    ppt_rect(s, 0.78, 5.25, 11.75, 0.82, "FFF4D8")
    ppt_box(s, 1.03, 5.48, 11.1, 0.35, "Accessibility score weights distance, travel time, capacity, and emergency service.", 12, INK)

    s = slide_base(prs, "Demo data and geographic scope")
    cards = [
        ("Population zones", str(COUNTS["population_areas"]), "fictional study areas", TEAL),
        ("Facilities", str(COUNTS["hospitals"]), "synthetic hospitals", NAVY),
        ("Road features", str(COUNTS["roads"]), "connected synthetic network", GREEN),
        ("Demand records", str(COUNTS["healthcare_demand"]), "annual synthetic histories", CORAL),
    ]
    for i, args in enumerate(cards):
        ppt_card(s, 0.72 + i * 3.15, 1.7, 2.85, *args)
    ppt_rect(s, 0.78, 3.68, 11.7, 1.56, "FFF4D8")
    ppt_box(s, 1.05, 3.94, 11, 0.3, "Geographic claim boundary", 13, NAVY, True)
    ppt_box(s, 1.05, 4.39, 11, 0.68, "Fictional study zones cluster near Chennai. Not all of Tamil Nadu, not official boundaries, and not observed data.", 14)
    ppt_box(s, 0.95, 5.75, 11.3, 0.78, "Inputs include polygon zones, age profiles, road speeds, facilities, exclusions, and deterministic demand values (2012–2025).", 12, GREY)

    s = slide_base(prs, "Demand model: synthetic-data evaluation")
    shape = s.shapes.add_table(4, 5, Inches(0.75), Inches(1.65), Inches(7.35), Inches(2.45))
    table = shape.table
    rows = [["Held-out test", "MAE", "RMSE", "R²", "MAPE"]]
    rows += [[name, f"{m.get('mae', 0):.2f}", f"{m.get('rmse', 0):.2f}", f"{m.get('r2', 0):.3f}", f"{m.get('mape', 0):.2f}%"] for name, m in MODELS]
    for ri, row in enumerate(rows):
        for ci, value in enumerate(row):
            cell = table.cell(ri, ci)
            cell.text = str(value)
            cell.fill.solid()
            cell.fill.fore_color.rgb = ppt_color(NAVY if ri == 0 else (WHITE if ri % 2 else SKY))
            for para in cell.text_frame.paragraphs:
                para.font.size = Pt(10)
                para.font.bold = ri == 0 or ci == 0
                para.font.color.rgb = ppt_color(WHITE if ri == 0 else INK)
    ppt_card(s, 8.45, 1.78, 3.85, "Selected model", "Linear regression", f"{T.get('records')} rows · selected by validation RMSE")
    ppt_rect(s, 8.45, 3.62, 3.85, 1.55, "FFF4D8")
    ppt_box(s, 8.72, 3.89, 3.2, 0.28, "TEMPORAL HOLDOUT", 10, NAVY, True)
    ppt_box(s, 8.72, 4.31, 3.2, 0.67, "Train 2013–19\nValidate 2020–22 · Test 2023–25", 12)
    ppt_box(s, 0.9, 4.6, 11.4, 0.88, "Strong fit here only reflects deterministic synthetic data. It is not evidence of clinical validity or accuracy on real populations.", 13, CORAL, True)

    s = slide_base(prs, "Baseline accessibility results")
    ppt_card(s, 0.78, 1.6, 2.9, "Modeled population", f"{A['population']:,}", "synthetic", TEAL)
    ppt_card(s, 3.9, 1.6, 2.9, "Mean travel time", f"{A['averageTravelTimeMinutes']:.2f} min", "road graph + access leg", NAVY)
    ppt_card(s, 7.02, 1.6, 2.9, "Mean access index", f"{A['meanAccessibilityIndex']:.3f}", "composite score 0–1", GREEN)
    ppt_card(s, 10.14, 1.6, 2.4, "Coverage", f"{A['coveragePercent']:.0f}%", "within 30 min", CORAL)
    dist = A["distribution"]
    ppt_rect(s, 0.82, 3.55, 11.65, 1.85, WHITE, outline="D9E2EC")
    ppt_box(s, 1.12, 3.82, 10.9, 0.3, "Accessibility classification across synthetic zones", 13, NAVY, True)
    x, full, total = 1.15, 10.9, max(sum(dist.values()), 1)
    for label, color in (("Good", GREEN), ("Moderate", GOLD), ("Poor", CORAL), ("Critical", "8B3A3A")):
        count = dist.get(label, 0)
        width = full * count / total
        if width:
            ppt_rect(s, x, 4.42, width, 0.36, color, False)
            ppt_box(s, x, 4.83, max(width, 0.5), 0.25, f"{label}: {count}", 9, INK, True, PP_ALIGN.CENTER)
            x += width
    ppt_box(s, 0.95, 5.78, 11.4, 0.78, "100% threshold coverage reflects this small connected demo network and is not a statewide finding.", 12, GREY)

    s = slide_base(prs, "Candidate generation and constraints")
    ppt_card(s, 0.8, 1.65, 3.1, "Feasible demo sites", str(C["count"]), "grid candidates", TEAL)
    ppt_rect(s, 4.25, 1.65, 8.05, 3.75, WHITE, outline="D9E2EC")
    ppt_box(s, 4.58, 1.98, 7, 0.34, "Screening sequence", 17, NAVY, True)
    items = (
        "Population and predicted-demand thresholds",
        "Minimum distance from existing hospitals",
        "Study boundary inclusion; water/protected exclusions",
        "Road-access score and grid spacing",
        "Equal site costs assumed; parcel prices absent",
    )
    for i, item in enumerate(items):
        y = 2.55 + i * 0.5
        ppt_rect(s, 4.62, y + 0.08, 0.11, 0.11, TEAL)
        ppt_box(s, 4.88, y, 7, 0.32, item, 12)
    ppt_rect(s, 0.82, 3.65, 3.1, 1.75, SKY)
    ppt_box(s, 1.1, 3.94, 2.5, 0.28, "SITE CONTEXT", 10, TEAL, True)
    ppt_box(s, 1.1, 4.35, 2.48, 0.75, "Candidates are not surveyed or verified parcels.", 12)
    ppt_box(s, 0.98, 5.78, 11.3, 0.7, "Geometry and thresholds do not replace land, environmental, transport, engineering, cost, or legal review.", 12, GREY)

    s = slide_base(prs, "Three-hospital scenario: modeled before / after")
    ppt_card(s, 0.82, 1.52, 3.0, "Mean travel time", f"{BEFORE['averageTravelTimeMinutes']:.2f} → {AFTER['averageTravelTimeMinutes']:.2f} min", "modeled, not measured", TEAL)
    ppt_card(s, 4.02, 1.52, 3.0, "Mean access index", f"{BEFORE['meanAccessibilityIndex']:.3f} → {AFTER['meanAccessibilityIndex']:.3f}", "composite score 0–1", GREEN)
    ppt_card(s, 7.22, 1.52, 2.5, "Feasible candidates", str(C["count"]), "three selected", NAVY)
    ppt_card(s, 9.92, 1.52, 2.5, "Relative cost", f"{O['estimatedCostUnits']:.0f} units", "assumed cost/site", CORAL)
    for x, label, left, right, vmax in (
        (0.98, "Mean road travel time (minutes)", BEFORE["averageTravelTimeMinutes"], AFTER["averageTravelTimeMinutes"], 10),
        (6.95, "Mean accessibility index (0–1)", BEFORE["meanAccessibilityIndex"], AFTER["meanAccessibilityIndex"], 1),
    ):
        ppt_box(s, x, 3.48, 5.3, 0.32, label, 12, NAVY, True)
        for i, (name, value, col) in enumerate((("Before", left, GREY), ("After", right, TEAL))):
            y = 3.98 + i * 0.52
            ppt_box(s, x, y, 0.88, 0.25, name, 9, GREY)
            ppt_rect(s, x + 0.98, y + 0.02, 3.45 * value / vmax, 0.22, col)
            ppt_box(s, x + 4.55, y - 0.03, 0.72, 0.28, f"{value:.2f}", 10, INK, True, PP_ALIGN.RIGHT)
    pct = (BEFORE["averageTravelTimeMinutes"] - AFTER["averageTravelTimeMinutes"]) / BEFORE["averageTravelTimeMinutes"] * 100
    ppt_box(s, 1.02, 5.42, 11.1, 0.88, f"Coverage remained {BEFORE['coveragePercent']:.0f}% at the 30-minute threshold. Modeled mean travel time fell {pct:.1f}%; the genetic algorithm is heuristic, not a global-optimality proof.", 12, INK, True)

    s = slide_base(prs, "Working application and validation")
    for i, (head, body) in enumerate(
        (
            ("Interactive Web GIS", "Dashboards, layers, maps, and role-aware screens"),
            ("Secure workflow", "JWT sign-in, role permissions, validation, audit events"),
            ("Long-running jobs", "Queued operations with progress and analysis history"),
            ("Outputs", "Recommendations and CSV / GeoJSON / PDF exports"),
        )
    ):
        y = 1.62 + i * 0.96
        ppt_rect(s, 0.84, y, 0.38, 0.38, TEAL)
        ppt_box(s, 0.88, y + 0.07, 0.3, 0.2, "✓", 12, WHITE, True, PP_ALIGN.CENTER)
        ppt_box(s, 1.45, y - 0.02, 3, 0.34, head, 15, NAVY, True)
        ppt_box(s, 4.65, y - 0.02, 7.5, 0.55, body, 12)
    ppt_rect(s, 0.85, 5.78, 11.65, 0.62, SKY)
    ppt_box(s, 1.08, 5.94, 11.1, 0.3, "Build passed · 3 frontend tests passed · frontend/API/ML health checks passed", 11, TEAL, True)

    s = slide_base(prs, "Limitations, responsible use, next steps")
    for x, head, items, bg, fg in (
        (0.8, "What the demo does not establish", ("Real demand or prediction accuracy", "Statewide coverage or official boundaries", "Parcel availability, cost, permits, feasibility", "Clinical benefit or global optimality"), WHITE, INK),
        (6.8, "Next steps before real deployment", ("Use licensed current regional data", "Validate by time and geography; assess bias", "Calibrate roads, costs, and constraints", "Review with planners and communities"), NAVY, "DCE7EF"),
    ):
        ppt_rect(s, x, 1.58, 5.75, 4.75, bg, outline="D9E2EC" if bg == WHITE else None)
        ppt_box(s, x + 0.3, 1.9, 5.0, 0.56, head, 16, NAVY if bg == WHITE else WHITE, True)
        for i, item in enumerate(items):
            y = 2.65 + i * 0.78
            ppt_rect(s, x + 0.32, y + 0.08, 0.11, 0.11, TEAL)
            ppt_box(s, x + 0.57, y, 4.85, 0.55, item, 12, fg)

    s = prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = ppt_color(NAVY)
    ppt_box(s, 0.95, 1.1, 11.4, 0.35, "TAKEAWAY", 11, "79D4C7", True)
    ppt_box(s, 0.95, 1.8, 11.2, 1.2, "A working planning prototype—\nnot a planning authority.", 30, WHITE, True)
    ppt_box(s, 1.0, 3.65, 10.9, 1.0, "It demonstrates how GIS, forecasting, feasibility screening, and optimization connect into one reviewable workflow.", 18, "DCE7EF")
    ppt_rect(s, 1.0, 5.15, 10.8, 0.82, "193B55")
    ppt_box(s, 1.3, 5.39, 10.2, 0.33, "Synthetic Chennai-area results must be replaced with validated regional data before policy use.", 13, "FFE0A3", True)
    ppt_box(s, 1.0, 6.65, 10, 0.3, "Thank you  |  Questions", 13, "79D4C7", True)
    prs.save(OUT / "Healthcare_Atlas_Project_Presentation.pptx")


def result_tables_docx(doc):
    rows = [
        ("Indicator", "Baseline", "After +3", "Interpretation"),
        ("Population coverage", f"{BEFORE['coveragePercent']:.1f}%", f"{AFTER['coveragePercent']:.1f}%", "Within 30-minute threshold"),
        ("Mean travel time", f"{BEFORE['averageTravelTimeMinutes']:.2f} min", f"{AFTER['averageTravelTimeMinutes']:.2f} min", "Modeled network travel"),
        ("Mean accessibility index", f"{BEFORE['meanAccessibilityIndex']:.3f}", f"{AFTER['meanAccessibilityIndex']:.3f}", "Composite score 0–1"),
        ("Relative site cost", "0 units", f"{O['estimatedCostUnits']:.0f} units", "Equal assumed cost/site"),
    ]
    table = doc.add_table(rows=0, cols=4)
    table.style = "Light Shading Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row in rows:
        cells = table.add_row().cells
        for cell, value in zip(cells, row):
            cell.text = str(value)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    doc.add_paragraph("Held-out temporal model comparison (synthetic test set):")
    mt = doc.add_table(rows=0, cols=5)
    mt.style = "Light Shading Accent 1"
    for row in [("Model", "MAE", "RMSE", "R²", "MAPE")] + [
        (name, f"{m.get('mae', 0):.2f}", f"{m.get('rmse', 0):.2f}", f"{m.get('r2', 0):.3f}", f"{m.get('mape', 0):.2f}%")
        for name, m in MODELS
    ]:
        for cell, value in zip(mt.add_row().cells, row):
            cell.text = str(value)
    doc.add_paragraph("Synthetic values do not indicate real-world predictive accuracy.")


def create_docx():
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin, sec.bottom_margin = DInches(0.72), DInches(0.72)
    sec.left_margin, sec.right_margin = DInches(0.82), DInches(0.82)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Aptos", DPt(10.5)
    normal.font.color.rgb = DRGB.from_string(INK)
    normal.paragraph_format.space_after = DPt(6)
    for name, size, color in (("Title", 29, NAVY), ("Heading 1", 18, TEAL), ("Heading 2", 13, NAVY)):
        style = doc.styles[name]
        style.font.name, style.font.size, style.font.bold = "Aptos Display", DPt(size), True
        style.font.color.rgb = DRGB.from_string(color)
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run("\n\n" + TITLE)
    run.bold, run.font.size = True, DPt(32)
    run.font.color.rgb = DRGB.from_string(NAVY)
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run(SUBTITLE)
    run.font.size, run.font.color.rgb = DPt(16), DRGB.from_string(TEAL)
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.add_run("\n\nPROJECT REPORT FOR SUBMISSION\n").bold = True
    para.add_run(
        f"Prepared {DATE}\n\nSubmitted by: ______________________________\n"
        "Institution / Department: ______________________________\n"
        "Supervisor: ______________________________\n\n"
    )
    run = para.add_run("SYNTHETIC CHENNAI-AREA DEMONSTRATION\nNot statewide · Not observed healthcare data")
    run.bold, run.font.color.rgb = True, DRGB.from_string(CORAL)
    doc.add_page_break()
    doc.add_heading("Submission note", 0)
    p = doc.add_paragraph()
    p.add_run("Data scope disclaimer. ").bold = True
    p.add_run("The executable demonstration uses synthetic fictional zones around Chennai. It is not official Tamil Nadu geography or real healthcare evidence. Do not report these outputs as observed findings or policy recommendations.")
    doc.add_heading("Contents", 0)
    for heading, _ in SECTIONS:
        doc.add_paragraph(heading, style="List Number")
    doc.add_page_break()
    for heading, paragraphs in SECTIONS:
        doc.add_heading(heading, level=1)
        if heading == "7. Results Tables":
            result_tables_docx(doc)
        for text in paragraphs:
            doc.add_paragraph(text)
    for section in doc.sections:
        header = section.header.paragraphs[0]
        header.text = "HEALTHCARE ATLAS  |  PROJECT REPORT"
        header.runs[0].font.color.rgb = DRGB.from_string(TEAL)
        header.runs[0].font.size = DPt(8)
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = footer.add_run("Synthetic Chennai-area demonstration · For academic project explanation only")
        run.font.size = DPt(8)
        run.font.color.rgb = DRGB.from_string(GREY)
    doc.save(OUT / "Healthcare_Atlas_Project_Report.docx")


def xml_escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def create_pdf():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitleX", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=27, leading=32, textColor=colors.HexColor("#" + NAVY), alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle(name="CoverSubX", parent=styles["Normal"], fontSize=14, leading=20, textColor=colors.HexColor("#" + TEAL), alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="H1X", parent=styles["Heading1"], fontSize=16, leading=20, textColor=colors.HexColor("#" + TEAL), spaceBefore=12, spaceAfter=7))
    styles.add(ParagraphStyle(name="BodyX", parent=styles["BodyText"], fontSize=9.5, leading=14, spaceAfter=7, textColor=colors.HexColor("#" + INK)))
    styles.add(ParagraphStyle(name="SmallX", parent=styles["BodyText"], fontSize=8, leading=11, textColor=colors.HexColor("#" + GREY)))
    story = [
        Spacer(1, 38 * mm),
        Paragraph(TITLE, styles["CoverTitleX"]),
        Paragraph(SUBTITLE, styles["CoverSubX"]),
        Spacer(1, 12 * mm),
        Paragraph(f"<b>PROJECT REPORT FOR SUBMISSION</b><br/><br/>Prepared {DATE}<br/><br/>Submitted by: ______________________________<br/><br/>Institution / Department: ______________________________<br/><br/>Supervisor: ______________________________", styles["BodyX"]),
        Spacer(1, 14 * mm),
        Paragraph("<b>SYNTHETIC CHENNAI-AREA DEMONSTRATION</b><br/>Not statewide · Not observed healthcare data", ParagraphStyle(name="DisclaimerX", parent=styles["BodyX"], alignment=TA_CENTER, textColor=colors.HexColor("#" + CORAL), fontSize=12, leading=17)),
        PageBreak(),
        Paragraph("Submission note", styles["H1X"]),
        Paragraph("<b>Data scope disclaimer.</b> The demonstration uses synthetic fictional zones around Chennai. It is not official Tamil Nadu geography or real healthcare evidence. Do not report these outputs as observed findings or policy recommendations.", styles["BodyX"]),
    ]
    for heading, paragraphs in SECTIONS:
        story.append(Paragraph(xml_escape(heading), styles["H1X"]))
        if heading == "7. Results Tables":
            data = [
                ["Indicator", "Baseline", "After +3", "Interpretation"],
                ["Population coverage", f"{BEFORE['coveragePercent']:.1f}%", f"{AFTER['coveragePercent']:.1f}%", "Within 30 min"],
                ["Mean travel time", f"{BEFORE['averageTravelTimeMinutes']:.2f} min", f"{AFTER['averageTravelTimeMinutes']:.2f} min", "Modeled"],
                ["Mean access index", f"{BEFORE['meanAccessibilityIndex']:.3f}", f"{AFTER['meanAccessibilityIndex']:.3f}", "0–1 score"],
                ["Relative cost", "0 units", f"{O['estimatedCostUnits']:.0f} units", "Assumed cost/site"],
            ]
            style = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#" + NAVY)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#" + SKY)]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
            story.extend([Table(data, repeatRows=1, colWidths=[35*mm, 26*mm, 26*mm, 75*mm], style=TableStyle(style)), Spacer(1, 4*mm)])
            md = [["Model", "MAE", "RMSE", "R²", "MAPE"]] + [
                [name, f"{m.get('mae', 0):.2f}", f"{m.get('rmse', 0):.2f}", f"{m.get('r2', 0):.3f}", f"{m.get('mape', 0):.2f}%"]
                for name, m in MODELS
            ]
            story.extend([Table(md, repeatRows=1, colWidths=[47*mm, 25*mm, 25*mm, 25*mm, 25*mm], style=TableStyle(style)), Spacer(1, 3*mm), Paragraph("Synthetic values do not indicate real-world predictive accuracy.", styles["SmallX"])])
        for text in paragraphs:
            story.append(Paragraph(xml_escape(text), styles["BodyX"]))

    def footer(canvas, doc):
        canvas.saveState()
        width, _ = A4
        canvas.setStrokeColor(colors.HexColor("#CBD5E0"))
        canvas.line(18*mm, 15*mm, width-18*mm, 15*mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#" + GREY))
        canvas.drawString(18*mm, 10*mm, "Synthetic Chennai-area demonstration · Academic project explanation")
        canvas.drawRightString(width-18*mm, 10*mm, str(doc.page))
        canvas.restoreState()

    SimpleDocTemplate(
        str(OUT / "Healthcare_Atlas_Project_Report.pdf"),
        pagesize=A4,
        rightMargin=18*mm,
        leftMargin=18*mm,
        topMargin=18*mm,
        bottomMargin=21*mm,
        title=SUBTITLE,
    ).build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    create_ppt()
    create_docx()
    create_pdf()
    for path in sorted(OUT.glob("Healthcare_Atlas_Project_*")):
        print(f"{path} ({path.stat().st_size:,} bytes)")
