#!/usr/bin/env python3
"""Create the first Project Polaris family naming workbook."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


OUTPUT = Path("output/pdf/Polaris_Naming_Workbook_v1.pdf")


CANDIDATES = {
    "Heritage and early astronomy": [
        "Alhazen", "Asterion", "Asteria", "Astrion", "Caelestis",
        "Cielon", "Coperniq", "Eudoxa", "Galenia", "Huygena",
        "Keplara", "Messiera", "Phaedra", "Sideris", "Tychon",
        "Urania", "Vesperion", "Zosma", "Ophiara", "Eraton",
    ],
    "Navigation and guidance": [
        "Aldara", "Azimora", "Bearing", "Celest", "Coursewise",
        "Dirion", "Farpoint", "Guidestar", "Lodestar", "Navora",
        "Northera", "Oriento", "Pathlight", "Sextara", "Starward",
        "Trueway", "Vantage", "Wayvera", "Zenira", "Zenithal",
    ],
    "Night readiness and confidence": [
        "Afterglow", "Clearcall", "Clearwise", "Darkwell", "Firstlight",
        "Nightform", "Nightlift", "Nightloom", "Nightora", "Nightwell",
        "Noctara", "Noctis", "Noxara", "Noxen", "Onsky",
        "Skyready", "Skymark", "Skyluma", "Sundown", "Twilora",
    ],
    "Light, optics, and clarity": [
        "Auralis", "Beamora", "Brillia", "Clarior", "Glimra",
        "Haloform", "Illuma", "Lensora", "Lucenta", "Luciora",
        "Lumenary", "Lumora", "Miravel", "Prismara", "Radiant",
        "Rayvera", "Spectara", "Stellume", "Virelia", "Visora",
    ],
    "Discovery and exploration": [
        "Aperion", "Deepway", "Farfield", "Fathom", "Findara",
        "Foresight", "Framelight", "Galivant", "Horizon", "Keenly",
        "Lookout", "Nextera", "Outward", "Questline", "Rovera",
        "Seekwell", "Surveyra", "Trailume", "Unfold", "Voyara",
    ],
    "Invented celestial brands": [
        "Arivon", "Atovia", "Avyra", "Calyro", "Cadria",
        "Celari", "Cendara", "Cielora", "Cireon", "Dovari",
        "Elaro", "Evarin", "Fyreli", "Galaro", "Ilyra",
        "Invara", "Kireli", "Lyren", "Mavara", "Nerova",
        "Novari", "Olyra", "Orivane", "Orvana", "Orynt",
        "Palora", "Quivra", "Roven", "Sereva", "Solvane",
        "Tavira", "Vaelor", "Veyra", "Vireli", "Zarela",
    ],
    "Premium and modern startup": [
        "Avenor", "Caelora", "Cadrin", "Celesyn", "Corvena",
        "Elaris", "Elion", "Evora", "Ilyon", "Liora",
        "Lunara", "Meridia", "Myria", "Novera", "Orlume",
        "Sidera", "Solara", "Valora", "Velaris", "Zerion",
    ],
    "Companion and action names": [
        "CaptureCue", "Framewise", "ImageNorth", "NightPilot", "NightSignal",
        "ScopeCue", "Scopewise", "Skybound", "SkySignal", "Starpath",
        "TargetCue", "Targetwise", "TimeToSky", "Tonightly", "TrueCapture",
        "Viewfinder", "Watchlight", "Wayfinder", "WhatNext", "YourSky",
    ],
}


TOP_25 = [
    ("Noctara", "Night-readiness name with a calm, premium feel. It implies nighttime without saying astronomy.", "High"),
    ("Lumora", "Light plus guidance energy. It is warm, memorable, and visually adaptable.", "High"),
    ("Cielora", "A coined name inspired by ciel, the French word for sky. Distinctive and elegant.", "High"),
    ("Navora", "Navigation-oriented without being tied to a single telescope brand or astronomy term.", "High"),
    ("Sidera", "From the Latin root for stars. Short, serious, and broad enough to grow with the company.", "High"),
    ("Auralis", "Suggests light, atmosphere, and intelligence. Strong premium visual territory.", "High"),
    ("Solvane", "Invented and active-sounding. It suggests solving the nightly decision without being literal.", "High"),
    ("Orivane", "A distinctive coined brand with an exploratory, forward-moving feel.", "High"),
    ("Veyra", "Short, modern, and app-icon friendly. Meaning would be defined by Polaris over time.", "High"),
    ("Calyro", "Compact invented name with a technical but approachable sound.", "Medium"),
    ("Caelora", "Sky-rooted, premium, and flexible for a consumer product or parent company.", "Medium"),
    ("Orynt", "Modern and directional. Very compact, but pronunciation would need testing.", "Medium"),
    ("Arivon", "Invented, clean, and scalable beyond a single astronomy function.", "Medium"),
    ("Cadria", "A memorable coined name that could support a compass, frame, or star-path visual identity.", "Medium"),
    ("Virelia", "Suggests vitality and light. More lyrical, with strong aesthetic potential.", "Medium"),
    ("Wayvera", "A guidance name with a subtle night-travel feeling. Slightly more descriptive than invented names.", "Medium"),
    ("Sextara", "A navigation throwback to sextants, with an approachable modern ending.", "Medium"),
    ("Keplara", "Honors Kepler while creating a more brand-like form. Historical territory needs careful clearance.", "Medium"),
    ("Alhazen", "A meaningful homage to a foundational figure in optics. Strong story, but requires deeper screening.", "Medium"),
    ("Astrion", "Directly celestial but less generic than Astro-prefixed names. Still needs crowding review.", "Medium"),
    ("Starward", "A clear sense of motion and aspiration. Very memorable, but likely crowded and needs deep review.", "Medium"),
    ("Firstlight", "Emotionally resonant for astrophotography. Descriptive territory is likely crowded.", "Medium"),
    ("NightPilot", "Communicates the product role immediately. Strong clarity, but less ownable than coined options.", "Medium"),
    ("ScopeCue", "Clear smart-telescope behavior: cue the next action. More functional than expansive.", "Medium"),
    ("TargetCue", "Very direct and beginner-friendly. Likely a useful product-feature name even if not the company name.", "Medium"),
]


def candidate_scores(name, category):
    """Transparent first-pass creative scores, not clearance research."""
    length = len(name)
    vowels = sum(letter.lower() in "aeiouy" for letter in name)
    memorability = 5 if 5 <= length <= 8 else 4 if length <= 10 else 3
    pronunciation = 5 if 2 <= vowels <= 4 and length <= 9 else 4
    brandability = 5 if category in {"Invented celestial brands", "Premium and modern startup"} else 4
    visual = 5 if length <= 8 else 4
    emotion = 5 if category in {"Night readiness and confidence", "Light, optics, and clarity"} else 4
    mission = 5 if category in {"Navigation and guidance", "Night readiness and confidence", "Companion and action names"} else 4
    return [memorability, pronunciation, brandability, visual, emotion, mission]


def score_label(scores):
    return f"{sum(scores)}/30"


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#2D5765"))
    canvas.line(0.6 * inch, 0.48 * inch, 7.9 * inch, 0.48 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6D94A0"))
    canvas.drawString(0.6 * inch, 0.28 * inch, "Project Polaris Naming Workbook - v1 - Internal family review")
    canvas.drawRightString(7.9 * inch, 0.28 * inch, f"Page {doc.page}")
    canvas.restoreState()


def add_title(story, title, subtitle, styles):
    story.append(Paragraph(title, styles["h1"]))
    story.append(Spacer(1, 0.10 * inch))
    story.append(Paragraph(subtitle, styles["subtitle"]))
    story.append(Spacer(1, 0.24 * inch))


def candidate_table(category, names, styles):
    rows = [["Name", "Initial fit", "Love", "Like", "Maybe", "Pass", "Notes"]]
    for name in names:
        scores = candidate_scores(name, category)
        rows.append([name, score_label(scores), "O", "O", "O", "O", ""])
    table = Table(rows, colWidths=[1.35 * inch, 0.72 * inch, 0.43 * inch, 0.43 * inch, 0.48 * inch, 0.40 * inch, 3.05 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A2430")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#E8F4F5")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F5FAFA")),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#102C38")),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8.4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F5FAFA"), colors.HexColor("#EAF4F5")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8D1D6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (1, 0), (5, -1), "CENTER"),
    ]))
    return table


def build_pdf():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=letter, rightMargin=0.6 * inch, leftMargin=0.6 * inch,
        topMargin=0.65 * inch, bottomMargin=0.7 * inch,
        title="Project Polaris Naming Workbook v1",
        author="Project Polaris",
    )
    base = getSampleStyleSheet()
    styles = {
        "cover": ParagraphStyle("cover", parent=base["Title"], fontName="Helvetica-Bold", fontSize=30, leading=34, textColor=colors.HexColor("#E8F4F5"), alignment=TA_CENTER),
        "cover_sub": ParagraphStyle("cover_sub", parent=base["Normal"], fontName="Helvetica", fontSize=13, leading=18, textColor=colors.HexColor("#A7D9DE"), alignment=TA_CENTER),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=21, leading=25, textColor=colors.HexColor("#102C38")),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=colors.HexColor("#0A6670")),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName="Helvetica", fontSize=10.5, leading=15, textColor=colors.HexColor("#476A74")),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName="Helvetica", fontSize=10, leading=14, textColor=colors.HexColor("#1A3640")),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName="Helvetica", fontSize=8.8, leading=12, textColor=colors.HexColor("#476A74")),
        "name": ParagraphStyle("name", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.HexColor("#102C38")),
    }
    story = []

    # Cover
    cover = Table([[Paragraph("PROJECT POLARIS", styles["cover"]), Paragraph("", styles["cover"])], [Paragraph("NAMING WORKBOOK", styles["cover"]), Paragraph("", styles["cover"])], [Paragraph("A family review of 175 first-pass brand candidates", styles["cover_sub"]), Paragraph("", styles["cover_sub"])]], colWidths=[4.9 * inch, 2.4 * inch], rowHeights=[1.55 * inch, 0.65 * inch, 1.0 * inch])
    cover.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#061923")),
        ("BOX", (0, 0), (-1, -1), 0, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 22),
        ("RIGHTPADDING", (0, 0), (-1, -1), 22),
    ]))
    story.extend([Spacer(1, 1.25 * inch), cover, Spacer(1, 0.35 * inch), Paragraph("Prepared for family discussion. Creative screening only - not a trademark, domain, app-store, or social-handle clearance report.", styles["small"]), PageBreak()])

    add_title(story, "How to use this workbook", "A name should earn emotional enthusiasm and survive practical screening.", styles)
    story.append(Paragraph("Start with instinct. Mark each candidate Love, Like, Maybe, or Pass. Do not overthink availability in this first round. Circle names that feel interesting, memorable, trustworthy, and worth saying aloud. Add notes on what you like or dislike about the sound, story, or visual feel.", styles["body"]))
    story.append(Spacer(1, 0.14 * inch))
    story.append(Paragraph("After the family reduces the list to roughly 10 finalists, Polaris will run deeper checks: App Store and Google Play search, domain and social-handle checks, USPTO preliminary search, web crowding review, and attorney-led trademark clearance before any public commitment.", styles["body"]))
    story.append(Spacer(1, 0.24 * inch))
    add_title(story, "What we are naming", "The product promise, not just an astronomy app.", styles)
    story.append(Paragraph("Polaris is an advisory companion for smart-telescope users. It turns conditions, equipment, available time, and imaging history into a clear answer to: <b>What should I do tonight?</b> The eventual public name should feel memorable, intriguing, credible, and ownable. Project Polaris remains an internal codename until a final name is selected and cleared.", styles["body"]))
    story.append(Spacer(1, 0.2 * inch))
    criteria = [["Initial creative screen", "What it means"], ["Memorability", "Easy to recall after hearing it once"], ["Pronunciation", "Comfortable to say and spell aloud"], ["Brandability", "Can grow beyond one feature or telescope"], ["Visual potential", "Works as an icon, wordmark, or badge"], ["Emotional appeal", "Feels inviting, capable, or intriguing"], ["Mission fit", "Feels aligned with guidance, readiness, and imaging confidence"]]
    t = Table(criteria, colWidths=[1.55 * inch, 5.75 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A6670")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#EFF8F8")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8D1D6")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LEADING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([t, PageBreak()])

    add_title(story, "My first-pass Top 25", "These are the best starting points for discussion - not approved or cleared names.", styles)
    top_rows = [["Name", "Why it stands out", "Screen", "Vote"]]
    for name, note, priority in TOP_25:
        top_rows.append([Paragraph(name, styles["name"]), Paragraph(note, styles["small"]), priority, "Love  Like  Maybe  Pass"])
    top = Table(top_rows, colWidths=[1.1 * inch, 4.15 * inch, 0.65 * inch, 1.4 * inch], repeatRows=1)
    top.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A2430")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F5FAFA")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8D1D6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 1), (-1, -1), 8.4),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([top, PageBreak()])

    for category, names in CANDIDATES.items():
        add_title(story, category, "Initial creative screen. Scores are subjective brand-fit ratings out of 30, not research findings.", styles)
        story.append(candidate_table(category, names, styles))
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph("Family notes: What themes, sounds, or emotional reactions keep repeating? Those patterns are often more useful than one isolated favorite.", styles["small"]))
        story.append(PageBreak())

    add_title(story, "Final family shortlist", "Bring forward no more than 10 names for real-world screening.", styles)
    shortlist_rows = [["Rank", "Candidate", "Why the family chose it", "Research result", "Decision"]]
    for rank in range(1, 11):
        shortlist_rows.append([str(rank), "", "", "", ""])
    shortlist = Table(shortlist_rows, colWidths=[0.45 * inch, 1.35 * inch, 2.9 * inch, 1.35 * inch, 1.25 * inch], rowHeights=[0.3 * inch] + [0.43 * inch] * 10)
    shortlist.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A6670")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F5FAFA")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#8FB6BD")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([shortlist, Spacer(1, 0.22 * inch), Paragraph("Next step: Polaris performs a preliminary web, app-store, domain, social-handle, and USPTO scan on the finalists. A trademark attorney should clear the final one or two candidates before public launch, company formation under the name, or paid brand work.", styles["body"])])

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build_pdf()
    print(OUTPUT)
