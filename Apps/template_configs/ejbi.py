"""
ejbi.py
-------
Template configuration for ejbi.tex

Journal: European Journal of Biomedical Informatics (EJBI)
Layout:  Opinion / Letter style — single-page two-column with:
         - TikZ absolute header/footer overlays
         - Gray tcolorbox metadata panel (correspondence + citation)
         - Numbered sections: Introduction, Discussion, Conclusion, References
Self-contained: all prompts, font, and layout defined here.
"""

from __future__ import annotations
from datetime import date, timedelta
from .base_template import BaseJournalTemplate


class EJBITemplate(BaseJournalTemplate):
    brand_name = "ejbi.tex"
    # Days for: [editor_assign, review, revise, publish]
    date_intervals = [3, 14, 2, 12]

    # ------------------------------------------------------------------
    # DATE LOGIC
    # ------------------------------------------------------------------
    def add_business_days(self, start_date: date, days: int) -> date:
        current_date = start_date + timedelta(days=days)
        while current_date.weekday() > 4:   # 5=Sat, 6=Sun
            current_date += timedelta(days=1)
        return current_date

    # ------------------------------------------------------------------
    # VOLUME / ISSUE FORMATTING
    # ------------------------------------------------------------------
    def format_volume_issue(self, volume: "int | str", issues: "int | str") -> "tuple[str, str]":
        v = f"0{volume}" if len(str(volume)) == 1 else str(volume)
        i = f"0{issues}" if len(str(issues)) == 1 else str(issues)
        return v, i

    # ------------------------------------------------------------------
    # TITLE FORMATTING
    # ------------------------------------------------------------------
    def format_title(self, generated_title: str) -> str:
        return generated_title.strip()

    # ------------------------------------------------------------------
    # MANUSCRIPT NUMBER FORMATTING
    # ------------------------------------------------------------------
    def format_manuscript_numbers(self, manuscript_no: str) -> dict:
        return {
            "QCNo": manuscript_no,
            "preQCNo": manuscript_no,
            "RManuNo": manuscript_no,
        }

    # ------------------------------------------------------------------
    # 1. INLINE CITATION FORMAT PROMPT
    # ------------------------------------------------------------------
    def get_citation_format_prompt(self) -> str:
        return (
            "author last name followed by first initial (e.g. Morgan K) — up to 6 authors, "
            "et al. for more — followed by year in parentheses, then article title, "
            "then journal short name, volume(issue):page range. "
            "(for example: 'Morgan K (2024). Transforming Healthcare through AI. EJBI. 20(4):274-275.')"
        )

    # ------------------------------------------------------------------
    # 2. HTML BODY SECTIONS
    # ------------------------------------------------------------------
    def get_html_body_sections(self, forHtml: dict) -> dict:
        return {
            "Introduction": forHtml.get("introduction", ""),
            "Discussion":   forHtml.get("discussion", ""),
            "Conclusion":   forHtml.get("conclusion", ""),
        }

    # ------------------------------------------------------------------
    # 3. LATEX FONT — Calibri (sffamily) for headers, Times New Roman for body
    # ------------------------------------------------------------------
    @property
    def latex_font(self) -> str:
        return ""

    # ------------------------------------------------------------------
    # 4. HTML REFERENCE — Author (year). Title. Journal, vol(iss):page.
    # ------------------------------------------------------------------
    def render_html_reference(self, count: int, ref: dict) -> str:
        title_query = "+".join(ref.get("title", "").split(" "))
        issues_str = (
            f"{ref.get('volume', '')}({ref.get('issues', '')})"
            if ref.get("issues")
            else f"{ref.get('volume', '')}"
        )
        return (
            f'<li><a name="{count}" id="{count}"></a>'
            f'{ref.get("authors_short", "")} ({ref.get("published", "")}). '
            f'<a href="{ref.get("url", "")}" target="_blank">'
            f'{ref.get("title", "")}</a>. '
            f'<i>{ref.get("journalShortName", "")}</i>. '
            f'{issues_str}:{ref.get("pageRangeOrNumber", "")}.'
            f'</li>'
        )

  # ------------------------------------------------------------------
    # 5. OUTPUT CITATION
    # ------------------------------------------------------------------
    def format_output_citation(self, author, title, short_journal, volume, issues, published, pdf_no) -> str:
        # Produces: "Morgan K (2024). Title. EJBI. 20(4):274-275."
        parts = author.split(" ")
        last = parts[0]
        initial = parts[1][0] if len(parts) > 1 else ""
        
        # Safely extract the year and force 4 digits if it's only 2
        year = str(published).split("-")[0].strip()
        if len(year) == 2:
            year = f"20{year}"
            
        return f"{last} {initial} ({year}). {title}. {short_journal}. {volume}({issues}):{pdf_no}."

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
            - Word count: 500-700.
            - Do not include any citations or citation markers (Strictly).
            - The Introduction must contain exactly 10 paragraphs, each corresponding to one reference.
            
            Description
            - Word count: 500-700.
            - Do not include any citations or citation markers (Strictly).
            - The Description must also contain exactly 10 paragraphs, each corresponding to one reference.

            Discussion
            - Word count: 200-400.
            - Include analysis, implications, or commentary derived from the content.
            -Do not include any citations or citation markers (Strictly).

            Summary (maps to Conclusion in the PDF)
            - Word count: 100-200.
            - Do not include citations (Strictly).
            - A crisp, declarative closing paragraph summarizing the key takeaway.

            Abstract
            - Word count: 90-100.
            - Provide a brief summary of the content.
            - No citations required.

            Keywords
            - Extract 5-8 keywords directly from the content.
            - Keywords should be in Title Case and separated by semi-colon(;).

            3. Writing Style
            - Formal academic tone appropriate for a biomedical informatics journal.
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

        IMPORTANT: Respond with ONLY the title. The title should be in title case, all articles and joining words should be in lower case (Example: Transforming Healthcare through Artificial Intelligence). No additional text, explanations, or formatting.
        """
