"""
amj_editorial.py
----------------
Template configuration for the Australasian Medical Journal (AMJ)
Editorial Note format.

Layout:   One-page editorial with red header banner, two-column body.
Compiler: XeLaTeX  (see amj_editorial.tex)
Fonts:
  - Main / body : Calibri  (sffamily — injected via preamble)
  - Headings    : Cambria  (rmfamily — set via fontspec mainfont alias in latex_font)
"""

from __future__ import annotations
import re
from datetime import date, timedelta
from .base_template import BaseJournalTemplate


class AmjEditorialTemplate(BaseJournalTemplate):
    """AMJ Editorial Note — single-page, two-column layout."""

    brand_name = "amj_editorial.tex"

    # Days for: [editor_assign, review, revise, publish]
    # Editorial notes skip the standard review cycle; keep minimal defaults.
    date_intervals = [1, 1, 1, 1]

    # ------------------------------------------------------------------
    # DATE LOGIC — calendar days, skip weekends to Monday
    # ------------------------------------------------------------------
    def add_business_days(self, start_date: date, days: int) -> date:
        """Add calendar days; if landing on Sat/Sun, advance to Monday."""
        current_date = start_date + timedelta(days=days)
        while current_date.weekday() > 4:   # 5=Sat, 6=Sun
            current_date += timedelta(days=1)
        return current_date

    # ------------------------------------------------------------------
    # LATEX FONT CONFIGURATION
    # Two fonts are used:
    #   • Calibri   → main/body font  (normalfont / sffamily)
    #   • Cambria   → roman serif font (rmfamily) used in header & headings
    # fontspec sets Calibri as \setmainfont so \normalfont and \sffamily
    # use Calibri; \setmainfont alias trick sets \rmfamily to Cambria.
    # ------------------------------------------------------------------
    @property
    def latex_font(self) -> str:
        return r"""
        \usepackage{fontspec}
        \usepackage{polyglossia}
        \setdefaultlanguage{english}
        % Heading / accent font: Cambria → \rmfamily (main roman font)
        \setmainfont{cambria.ttc}[
            Path=../../../Fonts/,
            BoldFont       = cambriab.ttf,
            ItalicFont     = cambriai.ttf,
            BoldItalicFont = cambriaz.ttf
        ]
        % Body font: Calibri → \sffamily / \normalfont via sans default
        \setsansfont{Calibri-Regular.ttf}[
            Path=../../../Fonts/,
            BoldFont       = Calibri-Bold.ttf,
            ItalicFont     = Calibri-Italic.ttf,
            BoldItalicFont = Calibri-BoldItalic.ttf
        ]
        % Make the document default to Calibri (sans) for body text
        \renewcommand{\familydefault}{\sfdefault}
        """

    # ------------------------------------------------------------------
    # HTML BODY SECTIONS
    # For an editorial note the body maps to the "introduction" slot
    # (the pipeline uses \VAR{introduction} for the main body text).
    # ------------------------------------------------------------------
    def get_html_body_sections(self, forHtml: dict) -> dict:
        return {
            "Editorial Note": forHtml.get("introduction", ""),
        }

    # ------------------------------------------------------------------
    # CITATION FORMAT PROMPT
    # Minimal — editorial notes don't include inline citations.
    # ------------------------------------------------------------------
    def get_citation_format_prompt(self) -> str:
        return (
            "author names (Last name, First initial) "
            "year. title. journal short name, volume(issue), page. "
            "(for example: 'Smith J 2022. Title. JournalShortName, 18(10), 1304.')"
        )

    # ------------------------------------------------------------------
    # HTML REFERENCE LIST ITEM
    # ------------------------------------------------------------------
    def render_html_reference(self, count: int, ref: dict) -> str:
        return (
            f'<li><a name="{count}" id="{count}"></a>'
            f'{ref.get("authors_short", "")} ({ref.get("published", "")}). '
            f'<a href="{ref.get("url", "")}" target="_blank">'
            f'"{ref.get("title", "")}"</a>. '
            f'<i>AMJ</i>, '
            f'{ref.get("volume", "")}({ref.get("issues", "")}), '
            f'{ref.get("pageRangeOrNumber", "")}.'
            f'</li>'
        )

    # ------------------------------------------------------------------
    # IN-TEXT CITATION OVERRIDES
    # ------------------------------------------------------------------
    def link_in_text_citations_html(self, forHtml: dict) -> dict:
        """Strip LLM-generated citations from the HTML output."""
        if "introduction" in forHtml:
            forHtml["introduction"] = re.sub(r'\[\d+(?:[,\-]\s*\d+)*\]\.?', '', forHtml["introduction"])
        return forHtml

    def link_in_text_citations_pdf(self, forPdf: dict) -> dict:
        """Strip LLM-generated citations from the PDF output."""
        if "introduction" in forPdf:
            forPdf["introduction"] = re.sub(r'\[\d+(?:[,\-]\s*\d+)*\]\.?', '', forPdf["introduction"])
        return forPdf

    # ------------------------------------------------------------------
    # OUTPUT CITATION
    # AMJ format: Author Year. Title. ShortName, Volume(Issue):PdfNo.
    # ------------------------------------------------------------------
    def format_output_citation(self, author, title, short_journal, volume, issues, published, pdf_no) -> str:
        year = published.split("-")[0] if "-" in published else published
        return f"{author} {year}. {title}. AMJ, {volume}({issues}):{pdf_no}."

    # ------------------------------------------------------------------
    # LLM PROMPT — STEP 1: REFERENCES
    # Editorial notes are hand-authored; this prompt is a minimal fallback.
    # ------------------------------------------------------------------
    def get_references_prompt(self, journal) -> str:
        return f"""
        You are provided with a topic:
        topic: "{journal.topic}"
        journal name: "Australasian Medical Journal"
        department: "{journal.authorsDepartment}"

        This is an editorial note, not a research article.
        Generate a structured output with a short editorial summary (subContent)
        and exactly 5 relevant references from the field described by the topic.
        All references must be authentic, peer-reviewed articles published within
        the last five years with at least three authors.

        The final structure should look like:
        "content": {{
            "C001": {{
                "subContent": "...",
                "references": "",
                "title": "...",
                "journalShortName": "...",
                "authors": ["...", "...", "..."],
                "published": "...",
                "pageRangeOrNumber": "...",
                "volume": "...",
                "issues": "...",
                "DOI": "...",
                "url": "...",
                "parentLink": "..."
            }},
            ... (C001 through C005)
        }}

        IMPORTANT: Your response must be ONLY a valid JSON object with no additional text,
        explanations, or markdown formatting. Do not include any text before or after the JSON.
        """

    # ------------------------------------------------------------------
    # LLM PROMPT — STEP 2: SECTIONS
    # For an editorial note the entire body goes into "introduction".
    # ------------------------------------------------------------------
    def get_sections_prompt(self, content_data: dict) -> str:
        return f"""
        You are given the following data: {content_data}

        This is an editorial note for a medical journal. Your task is to generate
        a warm, professionally written editorial note in JSON format.

        Output a valid JSON object with the following keys:

        "content": {{
            "introduction": "...",
            "description":  "...",
            "summary":      "...",
            "abstract":     "...",
            "discussion":   "...",
            "keywords":     "..."s
        }}

        For the "introduction" key, write the full editorial note body text
        (300-500 words). Include:
        - Summary of the current issue highlights
        - Acknowledgement of reviewers, editorial board, and authors
        - A forward-looking closing with an invitation to submit/review

        CRITICAL RULE FOR INTRODUCTION:
        DO NOT include ANY greetings like "Dear Readers," or "Season's greetings!".
        DO NOT include ANY sign-offs like "Sincerely, Editor".
        These are already hardcoded in the template. If you include them, they will appear twice.
        Begin your text IMMEDIATELY with the first sentence (e.g. "It is with immense pleasure that we present...").
        Write the text as a continuous narrative. You are strictly forbidden from using any reference markers, numbers, or brackets in the text (like [1], [2], etc.).

        For all other keys, provide brief appropriate content.
        Keywords: 5-8 topic-relevant terms separated by semi-colons.

        Writing style: professional, warm, human. No AI buzzwords or filler.

        IMPORTANT: Return ONLY the JSON object. No extra text, markdown, or commentary.
        """

    # ------------------------------------------------------------------
    # LLM PROMPT — STEP 3: TITLE
    # ------------------------------------------------------------------
    def get_title_prompt(self, summary: str) -> str:
        return f"""
        Generate a short editorial note title (4-6 words) based on this summary:
        {summary}

        The title should reflect the editorial nature, e.g. "Editor's Note: [Issue Theme]".

        IMPORTANT: Respond with ONLY the title. No additional text, explanations, or formatting.
        """

    # ------------------------------------------------------------------
    # TITLE FORMATTING
    # ------------------------------------------------------------------
    def format_title(self, generated_title: str) -> str:
        return generated_title.strip()
