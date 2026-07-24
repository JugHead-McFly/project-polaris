#!/usr/bin/env python3
"""Generate the desk-reference Polaris roadmap PDF."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "Project_Polaris_Roadmap_v1.pdf"

INK = colors.HexColor("#08202A")
DEEP = colors.HexColor("#0D2B36")
TEAL = colors.HexColor("#22C7BE")
SKY = colors.HexColor("#B9D8DE")
MIST = colors.HexColor("#EFF7F8")
LINE = colors.HexColor("#A7C7CD")
GOLD = colors.HexColor("#E8B44D")
GREEN = colors.HexColor("#57B889")
TEXT = colors.HexColor("#17333D")
MUTED = colors.HexColor("#527581")


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=31, leading=36, textColor=colors.white, alignment=TA_LEFT,
            spaceAfter=10,
        ),
        "cover_kicker": ParagraphStyle(
            "cover_kicker", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=9, leading=12, textColor=TEAL, tracking=1.7,
        ),
        "cover_text": ParagraphStyle(
            "cover_text", parent=base["Normal"], fontName="Helvetica",
            fontSize=15, leading=22, textColor=SKY,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=23, leading=28, textColor=INK, spaceAfter=7,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=13, leading=17, textColor=INK, spaceBefore=8, spaceAfter=5,
        ),
        "kicker": ParagraphStyle(
            "kicker", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8, leading=11, textColor=TEAL, tracking=1.4,
        ),
        "body": ParagraphStyle(
            "body", parent=base["BodyText"], fontName="Helvetica",
            fontSize=10.2, leading=14.2, textColor=TEXT, spaceAfter=5,
        ),
        "small": ParagraphStyle(
            "small", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.4, leading=11.3, textColor=MUTED,
        ),
        "table": ParagraphStyle(
            "table", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.2, leading=10.4, textColor=TEXT,
        ),
        "table_bold": ParagraphStyle(
            "table_bold", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=8.35, leading=10.4, textColor=INK,
        ),
        "table_head": ParagraphStyle(
            "table_head", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=8.35, leading=10.4, textColor=colors.white,
        ),
        "metric": ParagraphStyle(
            "metric", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=15.5, leading=18, textColor=INK,
        ),
        "metric_label": ParagraphStyle(
            "metric_label", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=7.4, leading=10, textColor=MUTED, tracking=1,
        ),
        "callout": ParagraphStyle(
            "callout", parent=base["BodyText"], fontName="Helvetica",
            fontSize=11.2, leading=15.5, textColor=INK,
        ),
    }


def p(text, style):
    return Paragraph(text, style)


def footer(canv, doc):
    canv.saveState()
    canv.setStrokeColor(LINE)
    canv.setLineWidth(0.6)
    canv.line(doc.leftMargin, 0.48 * inch, letter[0] - doc.rightMargin, 0.48 * inch)
    canv.setFont("Helvetica", 8)
    canv.setFillColor(MUTED)
    canv.drawString(doc.leftMargin, 0.28 * inch, "Project Polaris Roadmap - v1 - Internal planning")
    canv.drawRightString(letter[0] - doc.rightMargin, 0.28 * inch, f"Page {doc.page}")
    canv.restoreState()


def metric_box(label, value, note, s):
    box = Table(
        [[p(label.upper(), s["metric_label"])], [p(value, s["metric"])], [p(note, s["small"])]],
        colWidths=[2.12 * inch],
    )
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), MIST),
        ("BOX", (0, 0), (-1, -1), 0.75, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, 0), 11),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 11),
    ]))
    return box


def phase_row(version, window, outcome, gate, s, active=False):
    background = colors.HexColor("#E8F8F6") if active else colors.white
    name = f"<b>{version}</b><br/><font color='#527581'>{window}</font>"
    row = Table([[p(name, s["table"]), p(outcome, s["table"]), p(gate, s["table"])]],
                colWidths=[1.35 * inch, 2.72 * inch, 2.85 * inch])
    row.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BOX", (0, 0), (-1, -1), 0.55, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return row


def make_pdf():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    s = styles()
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter,
        leftMargin=0.72 * inch, rightMargin=0.72 * inch,
        topMargin=0.65 * inch, bottomMargin=0.72 * inch,
        title="Project Polaris Roadmap v1", author="Doug and Project Polaris",
    )
    story = []

    # Cover
    cover_content = [
        [p("PROJECT POLARIS", s["cover_kicker"])],
        [Spacer(1, 0.25 * inch)],
        [p("Roadmap to a\ntrusted private alpha", s["title"])],
        [Spacer(1, 0.12 * inch)],
        [p("A practical desk reference for turning a local astrophotography advisor into a small, evidence-led product.", s["cover_text"])],
        [Spacer(1, 1.15 * inch)],
        [p("NORTH STAR", s["cover_kicker"])],
        [Spacer(1, 0.08 * inch)],
        [p("Make astrophotography simpler without taking away the wonder of discovering the universe.", s["cover_text"])],
        [Spacer(1, 0.45 * inch)],
        [p("Version 1 | July 2026 | Internal planning document", s["small"])],
    ]
    cover = Table(cover_content, colWidths=[6.95 * inch], rowHeights=[None] * len(cover_content))
    cover.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 0.45 * inch),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0.45 * inch),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.extend([Spacer(1, 0.78 * inch), cover, PageBreak()])

    # Executive overview
    story.extend([
        p("EXECUTIVE ROADMAP", s["kicker"]),
        p("The shortest credible path", s["h1"]),
        p("Polaris has already learned much of the sky, how to make suggestions, how to plan a night, and how to show the result in Mission Control. The next step is not to add every good idea. It is to prove one repeatable habit: a smart-telescope user opens Polaris before imaging, understands the recommendation, and comes back because it made the night easier.", s["body"]),
        Spacer(1, 0.07 * inch),
    ])
    metrics = Table([[
        metric_box("Current state", "v1.6 local", "Working single-observatory product", s),
        metric_box("Work cadence", "10-14 hr/wk", "Focused sessions, not a full-time team", s),
        metric_box("Private alpha target", "Oct-Nov 2026", "10-20 invited users", s),
    ]], colWidths=[2.12 * inch] * 3, hAlign="LEFT")
    metrics.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story.extend([metrics, Spacer(1, 0.22 * inch)])

    story.append(p("TIMELINE", s["kicker"]))
    timeline = [
        ("NOW", "Finish Mission Control (v1.6)", "Validate the real local capture-to-learning loop.", TEAL),
        ("LATE JULY - EARLY AUG", "Listen to future explorers", "Learn the real pain; choose the smallest safe hosted design.", GOLD),
        ("AUGUST - SEPTEMBER", "Prepare the online observatory", "Onboard, recommend, explain, and collect useful feedback.", colors.HexColor("#5796C5")),
        ("OCTOBER - NOVEMBER", "Invite the First Explorers", "Invite 10-20 users only after the core flow is reliable.", GREEN),
        ("DECEMBER - FEBRUARY", "Closed beta decision", "Expand carefully if evidence shows repeat use and trust.", colors.HexColor("#8267AF")),
    ]
    timeline_rows = []
    for when, title, desc, color in timeline:
        marker = Table([["" ]], colWidths=[0.14 * inch], rowHeights=[0.44 * inch])
        marker.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color)]))
        timeline_rows.append([marker, p(f"<b>{when}</b><br/>{title}", s["table"]), p(desc, s["table"])])
    timeline_table = Table(timeline_rows, colWidths=[0.25 * inch, 2.2 * inch, 4.2 * inch])
    timeline_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (1, 0), (-1, -1), 0.45, LINE),
        ("BACKGROUND", (1, 0), (-1, -1), colors.white),
        ("LEFTPADDING", (1, 0), (-1, -1), 8),
        ("RIGHTPADDING", (1, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([timeline_table, Spacer(1, 0.18 * inch)])
    callout = Table([[p("<b>The decision rule:</b> do not publicly launch because a feature list feels complete. Launch only when real users repeatedly trust Polaris to reduce a real planning problem.", s["callout"])]], colWidths=[6.7 * inch])
    callout.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7E5")),
        ("BOX", (0, 0), (-1, -1), 0.75, GOLD),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
    ]))
    story.extend([callout, PageBreak()])

    # Milestones and gates
    story.extend([
        p("VERSION PLAN", s["kicker"]),
        p("What Polaris is learning next", s["h1"]),
        p("Dates are planning ranges. Each version exits only when its user-facing result is credible, not merely when its code compiles.", s["body"]),
    ])
    header = Table([[p("PLAIN-ENGLISH STEP", s["table_head"]), p("OUTCOME", s["table_head"]), p("EXIT TEST", s["table_head"])]], colWidths=[1.35 * inch, 2.72 * inch, 2.85 * inch])
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DEEP),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header)
    phases = [
        ("Finish Mission Control<br/>v1.6 / now", "Close the local single-user loop: plan, capture, ingest, review, and learn.", "Doug can complete that loop without manual database work.", True),
        ("Listen and choose<br/>2 weeks", "Log user pain and select one minimal hosted-product architecture.", "A written decision covers tenancy, security, deployment, data, backups, and monitoring.", False),
        ("Prepare the online observatory<br/>v1.7", "Add accounts, data isolation, secure configuration, and a deployable baseline.", "Two users cannot access or alter each other's observatory data.", False),
        ("Give a simple night plan<br/>v1.8", "Build mobile-friendly onboarding and the hosted tonight recommendation loop.", "A new user reaches a credible recommendation without Doug's help.", False),
        ("Make first visits trustworthy<br/>v1.9", "Make feedback, support, privacy basics, and reliability part of the product.", "Doug and 2-3 trusted testers use the core loop repeatedly without a critical failure.", False),
        ("Invite First Explorers<br/>v1.10", "Run private alpha with 10-20 invited smart-telescope users.", "Users return, understand the advice, and say they would miss Polaris.", False),
        ("Closed beta<br/>v2.0", "Run a controlled closed beta, expanding only on evidence.", "Service is stable and evidence supports continued investment or a change in direction.", False),
    ]
    for version, outcome, gate, active in phases:
        story.append(phase_row(version, "", outcome, gate, s, active=active))
    story.extend([Spacer(1, 0.17 * inch), p("What deliberately waits: native iOS/Android apps, subscriptions, broad device support, advanced image-processing workflows, and large feature expansion. They earn their place after the alpha proves repeat use.", s["small"]), PageBreak()])

    # Operating system
    story.extend([
        p("EXECUTION SYSTEM", s["kicker"]),
        p("How we keep the mountain small", s["h1"]),
        p("The plan should reduce overwhelm, not create more administration. We will use it to choose the next 100 feet of the climb.", s["body"]),
        p("Every time Doug says <b>Start coding timer</b>, the session begins with:", s["h2"]),
    ])
    session_rows = [
        [p("1", s["metric"]), p("<b>Current position</b><br/>Version, active milestone, and a short recap of what changed in the last few sessions.", s["body"])],
        [p("2", s["metric"]), p("<b>One outcome for today</b><br/>One clear result sized for the available 1-2 hour session, with only the next one or two tasks.", s["body"])],
        [p("3", s["metric"]), p("<b>Reality check</b><br/>Expected time, a real blocker, and the reason today matters to the private-alpha path.", s["body"])],
        [p("4", s["metric"]), p("<b>Close the loop</b><br/>Test, commit when appropriate, update the timer, and name the next smallest step.", s["body"])],
    ]
    session_table = Table(session_rows, colWidths=[0.48 * inch, 6.15 * inch])
    session_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8F8F6")),
        ("BOX", (0, 0), (-1, -1), 0.55, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.extend([session_table, Spacer(1, 0.16 * inch)])
    story.append(p("Completed foundation", s["h2"]))
    completed = [
        "Planner V3 produces chronological, equipment-aware advisory schedules.",
        "The operator dashboard separates tonight, portfolio, quality, history, data status, and location planning.",
        "Real capture ingestion now updates integration, history, and quality without changing the scientific source data.",
        "Backup checks, startup preflight, release gates, and a running project-time log protect the local product.",
        "Quality Scoring v2 and the goal engine are active v1.6 work, while product discovery and naming are documented separately.",
    ]
    done_rows = [[p("DONE", s["metric_label"]), p(item, s["body"])] for item in completed]
    done_table = Table(done_rows, colWidths=[0.62 * inch, 6.0 * inch])
    done_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF7EF")),
        ("BOX", (0, 0), (-1, -1), 0.55, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([done_table, Spacer(1, 0.16 * inch)])
    final = Table([[p("<b>Parallel business track:</b> naming, preliminary availability checks, a domain, a simple landing page, and launch-readiness work move alongside the product. We will ask qualified professionals to review decisions with legal or tax consequences. <br/><br/><b>Project-manager commitment:</b> I will flag scope creep, distinguish facts from guesses, and recommend the smallest useful next step.", s["callout"])]], colWidths=[6.7 * inch])
    final.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), MIST),
        ("BOX", (0, 0), (-1, -1), 0.75, TEAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
    ]))
    story.append(final)

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    make_pdf()
