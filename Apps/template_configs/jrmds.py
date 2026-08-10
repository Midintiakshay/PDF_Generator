"""
jrmds.py
--------
Template configuration for jrmds.tex

Journal: Journal of Research in Medical and Dental Science (JRMDS)
Layout:  A4 two-column case report style with:
         - fancyhdr running header/footer (1st page plain, 2+ pages with metadata)
         - Purple page-number badge in the footer
         - mdframed green citation box on page 1
         - multicols* two-column body
         - Numbered [1,2,3] in-text citation style
Self-contained: all prompts, font, and layout defined here.
"""

from __future__ import annotations
from datetime import date, timedelta
from .base_template import BaseJournalTemplate


class JrmdsTemplate(BaseJournalTemplate):
    brand_name = "jrmds.tex"

    # Days for: [editor_assign, review, revise, publish]
    date_intervals = [5, 14, 31, 7]   # calendar days (matches sample dates)

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
    # VOLUME / ISSUE FORMATTING — leave both as-is (no zero-padding)
    # ------------------------------------------------------------------
    def format_volume_issue(self, volume: "int | str", issues: "int | str") -> "tuple[str, str]":
        return str(volume), str(issues)

    # ------------------------------------------------------------------
    # TITLE FORMATTING — Title Case
    # ------------------------------------------------------------------
    def format_title(self, generated_title: str) -> str:
        return generated_title.strip()

    # ------------------------------------------------------------------
    # MANUSCRIPT NUMBER FORMATTING
    # e.g. base: JRMDS-25-170058
    #      QC  : JRMDS-25-170058
    #      preQC: JRMDS-25-170058 (PQ)  stored bare; suffix added in .tex
    #      RManu: JRMDS-25-170058 (R)   stored bare; suffix added in .tex
    # ------------------------------------------------------------------
    def format_manuscript_numbers(self, manuscript_no: str) -> dict:
        return {
            "QCNo":    manuscript_no,
            "preQCNo": manuscript_no,
            "RManuNo": manuscript_no,
        }

    # ------------------------------------------------------------------
    # MULTI-PASS PAGE COUNT — pdfNo is "001-00N" where N = total pages
    # ------------------------------------------------------------------
    needs_page_count_recompile: bool = True

    def build_pdf_no(self, page_count: int) -> str:
        """Returns page range like '01-03' using the real page count."""
        return f"01-{page_count:02d}"

    # ------------------------------------------------------------------
    # 1. INLINE CITATION FORMAT PROMPT
    # JRMDS uses numbered bracketed style [1,2]
    # ------------------------------------------------------------------
    def get_citation_format_prompt(self) -> str:
        return (
            "author last name followed by first two initials (e.g. Papara C, de Luca DA) — "
            "up to 6 authors, et al. for more — followed by article title, "
            "abbreviated journal name, year, volume, issue, and page range. "
            "(for example: 'Papara C, de Luca DA, Bieber K, et al. Morphea: The 2023 update. "
            "Front Med 2023; 13:1108623.')"
        )

    # ------------------------------------------------------------------
    # 2. HTML BODY SECTIONS — matches JRMDS case-report structure
    # ------------------------------------------------------------------
    def get_html_body_sections(self, forHtml: dict) -> dict:
        return {
            "Abstract":          forHtml.get("abstract", ""),
            "Keywords":          forHtml.get("keywords", ""),
            "Introduction":      forHtml.get("introduction", ""),
            "Description":       forHtml.get("description", ""),
            "Discussion":        forHtml.get("discussion", ""),
            "Conclusion":        forHtml.get("conclusion", ""),
        }

    # ------------------------------------------------------------------
    # 3. LATEX FONT — Times New Roman from local Fonts directory
    #    The .tex file inlines the fontspec block directly (no preamble
    #    injection needed) so this property returns an empty string.
    # ------------------------------------------------------------------
    @property
    def latex_font(self) -> str:
        return ""

    # ------------------------------------------------------------------
    # 4. HTML REFERENCE — numbered list, JRMDS style
    # ------------------------------------------------------------------
    def render_html_reference(self, count: int, ref: dict) -> str:
        issues_str = (
            f"{ref.get('volume', '')}({ref.get('issues', '')})"
            if ref.get("issues")
            else str(ref.get("volume", ""))
        )
        return (
            f'<li><a name="{count}" id="{count}"></a>'
            f'{ref.get("authors_short", "")} '
            f'<a href="{ref.get("parentLink", "")}" target="_blank">'
            f'{ref.get("title", "")}</a>. '
            f'<i>{ref.get("journalShortName", "")}</i> '
            f'{ref.get("published", "")}; '
            f'{issues_str}:{ref.get("pageRangeOrNumber", "")}.'
            f'</li>'
        )

    # ------------------------------------------------------------------
    # 5. OUTPUT CITATION — author, title, journal, year, vol (issue): page.
    # ------------------------------------------------------------------
    def format_output_citation(self, author, title, short_journal, volume, issues, published, pdf_no) -> str:
        year = str(published).split("-")[0].strip()
        return f"{author}, {title}, {short_journal}, {year}, {volume} ({issues}): {pdf_no}."

    # ------------------------------------------------------------------
    # 6. LLM PROMPT — STEP 1: REFERENCES
    # ------------------------------------------------------------------
    def get_references_prompt(self, journal) -> str:
        return f"""
        You are provided by a topic:
        topic : "{journal.topic}"
        journal name: "{journal.journalName}"
        department: "{journal.authorsDepartment}" ignore the university name if mentioned. use the department name only as reference.

        IMPORTANT: Generate a structured output for the given topic containing subContent (a concise summary of the article's key insights), references (complete citation-style entries), and all remaining required fields. All references must be authentic, peer-reviewed journal articles published within the last five years, each with at least three legitimate authors. Use only reputable journals indexed in PubMed, Scopus, or Web of Science. Every reference must include authors, year, title, journal name, volume, issue, page range, DOI, and a working URL that leads to the real article. Do not create or fabricate any data, authors, journals, DOIs, or links.

        The final structure should look like:
        "content": {{
        "C001": {{
            "subContent": "...",
            "references": "", # leave this empty; the backend will generate this string using citeAuthorFormat
            "title": "...",
            "journalShortName": "...",
            "authors": ["...", "...", "..."], # only three authors name (full name)
            "published": "...",
            "pageRangeOrNumber": "...", # the page range or the page number
            "volume": "...",
            "issues": "...",
            "DOI": "...",
            "url": "...", # pubmed link of the journal
            "parentLink": "..." # the particular article link
        }}, # give me exact 10 References(..., C009, C010)
        ...
        }}

        Focus on creating references from title, authors, year, and DOI.
        the most important thing, and the whole data will be copied out and used so give me clean information only the structured data no other thing not even a symbol or dot.
        note: Write like a confident, clear thinking human speaking to another smart human.
            Avoid robotic phrases like 'in today's fast-paced world', 'leveraging synergies', or furthermore.
            Skip unnecessary dashes (-), quotation marks (''), and corporate buzzwords like 'cutting-edge', 'robust', or 'seamless experience'. No AI tone. No fluff. No filler.
            Use natural transitions like 'here is the thing', 'let us break it down' or 'what this really means is'. Keep sentences varied in length and rhythm, like how real people speak or write. Prioritize clarity, personality, and usefulness.
            Every sentence should feel intentional, not generated.
        IMPORTANT: Your response must be ONLY a valid JSON object with no additional text,
            explanations, or markdown formatting. Do not include any text before or after the JSON.
        """

    # ------------------------------------------------------------------
    # 7. LLM PROMPT — STEP 2: SECTIONS
    # JRMDS case-report layout: Introduction, Description (Case/Methods),
    # Discussion, Conclusion
    # ------------------------------------------------------------------
    def get_sections_prompt(self, content_data: dict) -> str:
        return f"""
            You are given the following data: {content_data}
            You are also provided with reference details in the format: "C001", "C002", etc., where each reference contains full bibliographic information.

            Your task is to process this data and generate structured content in JSON format. Follow these instructions carefully:

            1. Output Structure
            Produce only a valid JSON object with the following keys:

            "content": {{
                "introduction": "...",
                "description": "...",
                "summary": "...", # Do not add any citations here
                "abstract": "...",
                "discussion": "...",
                "keywords": "..."
            }}

            - All sections must be filled.
            - Remove all special characters, escape sequences, and formatting symbols from the text.
            - Keep only brackets, commas, periods, and characters necessary for JSON and citation markers.

            2. Section Requirements

            Introduction
            - Word count: 300-500.
            - Include sequential citation markers from the references: "C001" -> [1], "C002" -> [2], and so on.
            - The Introduction must contain exactly 10 paragraphs, each corresponding to one reference.
            - The citation marker must be placed at the end of the paragraph, immediately before the period, followed by two line breaks(\\n).

            Description (serves as the Case Presentation / Methods section)
            - Word count: 400-600.
            - Include sequential citation markers: "C001" -> [1], "C002" -> [2], and so on.
            - The Description must also contain exactly 10 paragraphs, each corresponding to one reference.
            - The citation marker must be placed at the end of the paragraph, immediately before the period, followed by two line breaks(\\n).

            Discussion
            - Word count: 300-500.
            - Include analysis, implications, or clinical commentary derived from the content.
            - Include citation markers in ascending order, one per paragraph.

            Summary (maps to Conclusion in the PDF)
            - Word count: 100-200.
            - Do not include citations (Strictly).
            - A crisp, declarative closing paragraph summarizing the key takeaway.

            Abstract
            - Word count: 90-120.
            - Provide a brief summary of the case and its dental/clinical significance.
            - No citations required.

            Keywords
            - Extract 5-8 keywords directly from the content.
            - Keywords should be in Title Case and separated by commas.

            3. Writing Style
            - Formal academic / clinical tone appropriate for a medical and dental science journal.
            - Clear, concise sentences.
            - Avoid corporate buzzwords, filler, or AI-sounding phrases.
            - Use natural transitions and sentence variation.

            4. JSON Output Rules
            - Only return the JSON object.
            - No introductory phrases, explanations, or meta-commentary.
            - Ensure all text is clean and compliant with JSON formatting.
            """

    # ------------------------------------------------------------------
    # 8. LLM PROMPT — STEP 3: TITLE
    # ------------------------------------------------------------------
    def get_title_prompt(self, summary: str) -> str:
        return f"""
        Generate a 5-7 word title based on this summary: {summary}

        IMPORTANT: Respond with ONLY the title. The title should be in Title Case. No additional text, explanations, or formatting.
        """
