"""Erzeugt die deutsche Projekt-Dokumentation als PDF (docs/dokumentation.pdf).

Ausfuehrung:  python scripts/generate_pdf.py    (benoetigt: pip install .[docs])
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT = Path(__file__).resolve().parents[1] / "docs" / "dokumentation.pdf"

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1x", parent=styles["Heading1"], spaceBefore=18, spaceAfter=8)
H2 = ParagraphStyle("H2x", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6)
BODY = ParagraphStyle("Bodyx", parent=styles["BodyText"], fontSize=10.5, leading=15,
                      spaceAfter=6)
CODE = ParagraphStyle("Codex", parent=styles["Code"], fontSize=9, leading=12,
                      backColor=colors.whitesmoke, borderPadding=6, spaceAfter=8)
NOTE = ParagraphStyle("Notex", parent=BODY, backColor=colors.Color(1, 0.96, 0.88),
                      borderPadding=8, spaceBefore=6, spaceAfter=10)


def p(text: str, style=BODY) -> Paragraph:
    return Paragraph(text, style)


def bullets(items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(p(i), leftIndent=6) for i in items],
        bulletType="bullet", start="•", spaceAfter=8,
    )


def build() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="AI Stock Research Assistant – Dokumentation",
        author="AI Stock Research Assistant",
    )
    e: list = []

    # Titel
    e.append(Paragraph("AI Stock Research Assistant", styles["Title"]))
    e.append(p(f"<i>Technische Dokumentation – Stand {dt.date.today().isoformat()}</i>"))
    e.append(Spacer(1, 6))
    e.append(p(
        "<b>Wichtiger Hinweis:</b> Dieses Werkzeug und alle damit erzeugten "
        "Reports dienen ausschließlich Informations- und Ausbildungszwecken. "
        "Sie stellen <b>keine Anlageberatung</b> und keine Kauf- oder "
        "Verkaufsempfehlung dar. KI-generierte Analysen können Fehler enthalten. "
        "Zielgruppe dieser Dokumentation: technisch interessierte Privatanleger.",
        NOTE))

    # 1. Was macht das Tool?
    e.append(p("1. Was macht das Tool?", H1))
    e.append(p(
        "Der AI Stock Research Assistant ist ein Kommandozeilen-Werkzeug (mit "
        "optionalem lokalem Web-UI), das aus einem einzelnen Ticker-Symbol "
        "(z.&nbsp;B. <b>AAPL</b>) ein strukturiertes Research-Memo im Stil eines "
        "Analysten-Reports erzeugt. Dazu sammelt es automatisch Kursdaten, "
        "Fundamentalkennzahlen, den makroökonomischen Kontext und aktuelle "
        "Unternehmensnachrichten und lässt diese Daten von einem großen "
        "Sprachmodell (Anthropic Claude) interpretieren."))
    e.append(p("Typische Aufrufe:", BODY))
    e.append(p(
        "research AAPL<br/>"
        "research AAPL --deep<br/>"
        "research --compare AAPL MSFT<br/>"
        "research AAPL --offline", CODE))
    e.append(p(
        "Pro Ticker entstehen zwei Dateien im Verzeichnis <b>reports/</b>: ein "
        "Markdown-Memo (für Menschen) und eine JSON-Datei mit sämtlichen "
        "Rohkennzahlen (für Maschinen bzw. eigene Auswertungen)."))

    # 2. Pipeline
    e.append(p("2. Wie funktioniert die Pipeline – Schritt für Schritt", H1))
    e.append(p("Schritt 1: Datenbeschaffung", H2))
    e.append(bullets([
        "<b>Kursdaten &amp; Fundamentals (yfinance):</b> aktueller Kurs, "
        "Marktkapitalisierung, Bewertungskennzahlen (KGV, P/B, P/S, EV/EBITDA, "
        "PEG), Margen (Brutto, operativ, netto), Wachstum (Umsatz, Gewinn), "
        "Verschuldung (Debt/Equity, Current Ratio), Free Cashflow, "
        "Dividendenrendite, Beta und 52-Wochen-Spanne. Zusätzlich wird aus einem "
        "Jahr Kurshistorie die 1-Jahres-Rendite und die annualisierte "
        "Volatilität berechnet.",
        "<b>Makro-Kontext (FRED API):</b> Rendite 10-jähriger US-Staatsanleihen "
        "(DGS10), US-Leitzins (FEDFUNDS), CPI-Inflation im Jahresvergleich "
        "(CPIAUCSL) und US-Arbeitslosenquote (UNRATE).",
        "<b>News (yfinance-News-Feed):</b> die aktuellsten Schlagzeilen zum "
        "Unternehmen mit Quelle und Zeitstempel.",
    ]))
    e.append(p(
        "Alle Daten werden zu einem <i>DataBundle</i> zusammengefasst – der "
        "einzigen Datenquelle für alle folgenden Schritte. Im Offline-Modus "
        "(--offline) wird stattdessen ein aufgezeichneter Snapshot geladen."))
    e.append(p("Schritt 2 bis 5: Vierstufige KI-Analyse", H2))
    e.append(bullets([
        "<b>Fundamentalanalyse:</b> Interpretation von Bewertung, Wachstum, "
        "Margen und Verschuldung.",
        "<b>Qualitative Einschätzung:</b> möglicher Burggraben (Moat), "
        "wesentliche Risiken, Branchenlage – unter Einbezug von Makro-Umfeld "
        "und Schlagzeilen.",
        "<b>Bull Case / Bear Case:</b> je drei (Standard) bzw. fünf (--deep) "
        "Argumente für das positive und das negative Szenario.",
        "<b>Research-Memo:</b> ein Executive Summary, das alle vorherigen "
        "Stufen verdichtet – bewusst ohne Kursziel und ohne Empfehlung.",
    ]))
    e.append(p(
        "Jede Stufe ist ein eigener API-Aufruf an die Anthropic Messages API "
        "(Standard-Modell: <b>claude-sonnet-5</b>, konfigurierbar über die "
        "Umgebungsvariable STOCK_RESEARCH_MODEL). Die Memo-Stufe erhält die "
        "Ergebnisse der vorherigen Stufen als Kontext."))
    e.append(p("Schritt 6: Report-Generierung", H2))
    e.append(p(
        "Der Report-Generator setzt das Markdown-Memo zusammen. Wichtig: Die "
        "<b>Kennzahlenübersicht wird nicht vom Sprachmodell erzeugt</b>, sondern "
        "deterministisch aus den Rohdaten gerendert. Das Modell liefert nur die "
        "Interpretation – die Tabelle ist damit garantiert konsistent mit den "
        "Rohdaten. Jeder Report beginnt mit einem deutlichen Disclaimer."))

    # 3. Datenquellen
    e.append(p("3. Datenquellen im Detail", H1))
    table = Table(
        [
            ["Quelle", "Inhalt", "Zugang"],
            ["Yahoo Finance\n(via yfinance)", "Kurse, Fundamentals, News",
             "ohne Key (inoffizielle API)"],
            ["FRED\n(St. Louis Fed)", "Zinsen, Inflation,\nArbeitsmarkt",
             "kostenloser API-Key\n(FRED_API_KEY)"],
            ["Anthropic API", "KI-Analyse\n(claude-sonnet-5)",
             "API-Key (ANTHROPIC_API_KEY)"],
        ],
        colWidths=[4.2 * cm, 6.0 * cm, 5.6 * cm],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.15, 0.25, 0.45)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    e.append(table)
    e.append(Spacer(1, 8))
    e.append(p(
        "Alle Schlüssel werden ausschließlich über Umgebungsvariablen bzw. eine "
        "lokale .env-Datei geladen (python-dotenv). Im Repository liegt nur eine "
        ".env.example mit Platzhaltern; die echte .env ist per .gitignore "
        "ausgeschlossen."))

    # 4. Prompt-Aufbau
    e.append(p("4. Wie ist der Prompt aufgebaut?", H1))
    e.append(p(
        "Jeder API-Aufruf besteht aus einem <b>System-Prompt</b> und einem "
        "<b>Daten-Prompt</b>. Der System-Prompt definiert die Rolle "
        "(nüchterner Aktienanalyst, Deutsch) und die Sicherheitsregeln:"))
    e.append(bullets([
        "Nur die im Prompt gelieferten Daten verwenden – keine Zahlen erfinden.",
        "Kennzahlen exakt übernehmen (Dezimalpunkt-Schreibweise, z. B. 32.5); "
        "fehlende Werte als fehlend benennen, nicht schätzen.",
        "Keine Kursziele, keine Kauf-/Verkaufsempfehlungen, keine Anlageberatung.",
        "Sachliches, strukturiertes Markdown.",
    ]))
    e.append(p(
        "Der Daten-Prompt enthält die vollständigen Rohdaten in drei Formen: als "
        "formatierte Kennzahlen-Tabelle, als Makro-/News-Zusammenfassung und "
        "zusätzlich als JSON-Block – gefolgt von der konkreten Aufgabe der "
        "jeweiligen Pipeline-Stufe (inkl. gewünschter Länge und Gliederung). "
        "Die Memo-Stufe bekommt zusätzlich die Texte der drei vorherigen Stufen."))
    e.append(p(
        "Diese Redundanz (Tabelle + JSON) reduziert Zahlendreher; die strikte "
        "Vorgabe der Dezimalpunkt-Schreibweise macht die Ausgaben maschinell "
        "prüfbar (siehe Abschnitt 6, Halluzinations-Check)."))

    # 5. Report lesen
    e.append(PageBreak())
    e.append(p("5. Wie liest man einen Report?", H1))
    e.append(bullets([
        "<b>Kopfzeile:</b> Erstellungszeit, verwendeter Analyst (Claude-Modell "
        "oder Offline-Template), Datenstand und Datenquelle (live/fixture).",
        "<b>Disclaimer:</b> steht bewusst ganz oben – bitte ernst nehmen.",
        "<b>Executive Summary:</b> die Kernthese in wenigen Sätzen. Guter "
        "Startpunkt, ersetzt aber nicht die Details.",
        "<b>Kennzahlenübersicht:</b> deterministisch aus den Rohdaten erzeugt. "
        "„n/a“ bedeutet: Yahoo Finance liefert diesen Wert für das "
        "Unternehmen nicht (häufig bei Banken, z. B. Debt/Equity).",
        "<b>Makro-Umfeld:</b> Zins- und Inflationskontext, der Bewertungen "
        "(insbesondere KGV) einordnet.",
        "<b>Fundamentalanalyse / Qualitative Einschätzung:</b> die "
        "KI-Interpretation. Aussagen sind Einschätzungen, keine Fakten.",
        "<b>Bull/Bear Case:</b> beide Seiten lesen! Die Struktur zwingt zu "
        "einer ausgewogenen Betrachtung.",
        "<b>Aktuelle News:</b> Schlagzeilen als Kontext – Details bitte in der "
        "Originalquelle prüfen.",
        "<b>Datenquellen &amp; Methodik:</b> woher die Daten stammen und wie "
        "der Report entstand.",
    ]))
    e.append(p(
        "Faustregel: Die Kennzahlen-Tabelle ist „hart“ (direkt aus den "
        "Daten), der Fließtext ist „weich“ (KI-Interpretation). Wer "
        "eine Zahl aus dem Fließtext weiterverwendet, sollte sie gegen die "
        "Tabelle bzw. die JSON-Datei prüfen."))

    # 6. Qualitaetssicherung
    e.append(p("6. Qualitätssicherung: Tests und Eval-Suite", H1))
    e.append(p(
        "Neben klassischen Unit-Tests (Datenparsing, Formatierung, CLI) bringt "
        "das Projekt eine Eval-Suite mit, die zehn bekannte Ticker analysiert "
        "und jeden erzeugten Report automatisch prüft:"))
    e.append(bullets([
        "<b>(a) Pflicht-Sektionen:</b> Executive Summary, Kennzahlenübersicht, "
        "Makro-Umfeld, Fundamentalanalyse, Qualitative Einschätzung, Bull/Bear "
        "Case, News, Methodik und Disclaimer müssen vorhanden sein.",
        "<b>(b) Kennzahlen-Konsistenz:</b> jeder Zahlwert der "
        "Kennzahlenübersicht wird gegen die Rohdaten geprüft (relative Toleranz "
        "0.5 % plus Rundungstoleranz).",
        "<b>(c) Halluzinations-Check:</b> jede Zahl im KI-Fließtext muss sich "
        "auf einen Rohdatenwert (oder eine übliche Skalierung wie Prozent oder "
        "Mrd.) zurückführen lassen (relative Toleranz 5 %). Unbelegte Zahlen "
        "führen zum Nichtbestehen.",
    ]))
    e.append(p(
        "Die Ergebnisse landen in evals/results.json; die Trefferquote ist im "
        "README dokumentiert. Die Suite läuft wahlweise offline (aufgezeichnete "
        "Snapshots + regelbasierter Analyst, z. B. in CI) oder mit --live gegen "
        "echte Daten und die echte Anthropic API."))

    # 7. Grenzen
    e.append(p("7. Bekannte Grenzen", H1))
    e.append(bullets([
        "<b>Keine Anlageberatung</b> und keine geprüfte Finanzanalyse.",
        "<b>Datenqualität:</b> yfinance nutzt inoffizielle "
        "Yahoo-Finance-Schnittstellen; Werte können fehlen, verzögert oder "
        "fehlerhaft sein. Das Format des News-Feeds ändert sich gelegentlich.",
        "<b>LLM-Grenzen:</b> Der Halluzinations-Check prüft Zahlen, nicht "
        "Argumentationslogik. Fehlinterpretationen bleiben möglich.",
        "<b>US-Fokus:</b> Die Makro-Serien stammen aus US-Quellen (FRED); für "
        "nicht-US-Aktien ist der Makro-Kontext nur bedingt aussagekräftig.",
        "<b>Momentaufnahme:</b> Ein Report spiegelt den Datenstand zum "
        "Abrufzeitpunkt wider – er veraltet schnell.",
        "<b>Kein Backtest:</b> Die Eval-Suite misst Report-Qualität und "
        "Datenkonsistenz, nicht die Prognosegüte der Analysen.",
        "<b>Kosten:</b> Jede Analyse verursacht API-Kosten (vier Aufrufe pro "
        "Ticker, mehr im --compare-Modus).",
    ]))

    doc.build(e)
    print(f"PDF geschrieben: {OUT}")


if __name__ == "__main__":
    build()
