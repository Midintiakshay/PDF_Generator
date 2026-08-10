"""
ab_academies.py
---------------
Template configuration for ABAcademies.tex

Self-contained: all prompts, font, and layout defined here.
"""

from __future__ import annotations
from datetime import date, timedelta
from .base_template import BaseJournalTemplate


class ABAcademiesTemplate(BaseJournalTemplate):
    brand_name = "ABAcademies.tex"
    #: Days for each workflow stage [editor_assign, review, revise, publish]
    date_intervals = [2, 14, 5, 7]     # calendar days

    # ------------------------------------------------------------------
    # 0a. MULTI-PASS FLAG — trigger a 3rd xelatex run once page count is known
    # ------------------------------------------------------------------
    needs_page_count_recompile: bool = True

    # ------------------------------------------------------------------
    # VOLUME / ISSUE FORMATTING — issues: no zero-padding; volume: zero-padded
    # ------------------------------------------------------------------
    def format_volume_issue(self, volume: "int | str", issues: "int | str") -> "tuple[str, str]":
        """
        ABAcademies: volume is zero-padded when single-digit, but issues is
        always returned as-is (no leading zero).
        """
        v = f"0{volume}" if len(str(volume)) == 1 else str(volume)
        i = str(issues)   # never zero-pad issues for this brand0979
        return v, i

    def build_pdf_no(self, page_count: int) -> str:
        """
        ABAcademies citation format requires a page range: "1-{total_pages}".
        Called by the pipeline after the first-pass PDF is compiled.
        """
        return f"1-{page_count}"

    # ------------------------------------------------------------------
    # 0. DATE LOGIC — calendar days, skip weekends to Monday
    # ------------------------------------------------------------------
    # def add_business_days(self, start_date: date, days: int) -> date:
    #     """Add calendar days; if landing on Sat/Sun, advance to Monday."""
    #     current_date = start_date + timedelta(days=days)
    #     while current_date.weekday() > 4:   # 5=Sat, 6=Sun
    #         current_date += timedelta(days=1)
    #     return current_date

    # ------------------------------------------------------------------
    # 0. DATE LOGIC — weekdays only
    # ------------------------------------------------------------------
    def add_business_days(self, start_date: date, days: int) -> date:
        current_date = start_date
        added_days = 0
        while added_days < days:
            current_date += timedelta(days=1)
            if current_date.weekday() < 5:          # Mon-Fri
                added_days += 1
        return current_date

    # ------------------------------------------------------------------
    # 1. INLINE CITATION FORMAT PROMPT
    # ------------------------------------------------------------------
    def get_citation_format_prompt(self) -> str:
        return (
            "author full name (Last name, First name — 3 to 6 authors separated with comma) "
            "(year of publishing inside parenthesis). "
            "title of that journal. Journal short name, Volume(issue), page range or article number. "
            "DOI link. "
            "(for example: 'Smith, John, Doe, Alice, Lee, Bob (2022). "
            "Title of the Article. JournalShortName, 15(3), 200-215. https://doi.org/...')"
        )

    # ------------------------------------------------------------------
    # 2. HTML BODY SECTIONS — includes Abstract, Keywords, Discussion
    # ------------------------------------------------------------------
    def get_html_body_sections(self, forHtml: dict) -> dict:
        return {
            "Abstract": forHtml.get("abstract", ""),
            "Keywords": forHtml.get("keywords", ""),
            "Introduction": forHtml.get("introduction", ""),
            "Description": forHtml.get("description", ""),
            "Discussion": forHtml.get("discussion", ""),
            "Conclusion": forHtml.get("conclusion", ""),
        }

    # ------------------------------------------------------------------
    # 3. LATEX FONT — Times New Roman
    # ------------------------------------------------------------------
    @property
    def latex_font(self) -> str:
        return r"""
        \usepackage{fontspec}
        \setmainfont{Times New Roman}[
            Path=../../../Fonts/,
            UprightFont    = * ,
            BoldFont       = *-Bold ,
            ItalicFont     = *-Italic ,
            BoldItalicFont = *-BoldItalic
        ]"""

    # ------------------------------------------------------------------
    # 4. HTML REFERENCE — author (year). title. italic journal, vol(iss):page
    # ------------------------------------------------------------------
    def render_html_reference(self, count: int, ref: dict) -> str:
        title_query = "+".join(ref.get("title", "").split(" "))
        return (
            f'<li><a name="{count}" id="{count}"></a>'
            f'{ref.get("authors_full", "")} ({ref.get("published", "")}). '
            f'<a href="{ref.get("parentLink", "")}" target="_blank">{ref.get("title", "")}</a>. '
            f'<i>{ref.get("journalShortName", "")}</i>, '
            f'{ref.get("volume", "")}({ref.get("issues", "")}), {ref.get("pageRangeOrNumber", "")}.'
            f'<p align="right">'
            f'<a href="{ref.get("url", "")}" target="_blank"><u>Indexed at</u></a>, '
            f'<a href="https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5&q={title_query}&btnG=" target="_blank"><u>Google Scholar</u></a>, '
            f'<a href="https://doi.org/{ref.get("DOI", "")}" target="_blank"><u>Crossref</u></a>'
            f'</p></li>'
        )

    # ------------------------------------------------------------------
    # 5. OUTPUT CITATION
    # ------------------------------------------------------------------
    def format_output_citation(self, author, title, short_journal, volume, issues, published, pdf_no) -> str:
        parts = author.split(" ")
        year = published.split("-")[-1]
        last = parts[-1]
        first = " ".join(parts[:-1])
        return f"{last}, {first} ({year}). {title}. {short_journal}, {volume}({issues}), {pdf_no}."

    # ------------------------------------------------------------------
    # 6. LLM PROMPT — STEP 1: REFERENCES
    # ------------------------------------------------------------------
    def get_references_prompt(self, journal) -> str:
        return f"""
        You are provided by a topic:
        topic : "{journal.topic}"
        journal name: "{journal.journalName}"
        department: "{journal.authorsDepartment}" ignore the university name if mentioned. use the department name only as reference.
        ...
        IMPORTANT: Generate a structured output for the given topic containing subContent (a concise summary of the article's key insights), references (complete citation-style entries), and all remaining required fields. All references must be authentic, peer-reviewed journal articles published within the last five years, each with at least three legitimate authors. Use only reputable journals indexed in PubMed, Scopus, or Web of Science. Every reference must include authors, year, title, journal name, volume, issue, page range, DOI, and a working URL that leads to the real article. Do not create or fabricate any data, authors, journals, DOIs, or links.


        The final structure should look like:
        "content": {{
        "C001": {{
            "subContent": "...",
            "references": "", # leave this empty; the backend will generate this string using citeAuthorFormat
            "title": "...",
            "journalShortName": "...",
            "authors": ["...", "...", "..."], #only three authors name (full name)
            "published": "...",
            "pageRangeOrNumber": "...", #the page range or the page number, that is it.
            "volume": "...",
            "issues": "...",
            "DOI": "...",
            "url": "...", # pubmed link of the journal
            "parentLink": "..." # the perticular article link
        }}, # give me exact 10 References(..., C009, C010)
        ...
        }}

        Focus on creating references from title, authors, year, and DOI.
        the most important thing, and the whole data will be copied out and used so give me clean information only the structured data no other thing not even a symbol or dot.
        note: Write like a confident, clear thinking human speaking to another smart human.
            Avoid robotic phrases like 'in today's fast-paced world', 'leveraging synergies', or furthermore.
            Skip unnecessary dashes (-), quotation marks (''), and corporate buzzwords like 'cutting-edge', 'robust', or 'seamless experience'. No AI tone. No fluff. No filler.
            Use natural transitions like 'here's the thing', 'let's break it down' or 'what this really means is'. Keep sentences varied in length and rhythm, like how real people speak or write. Prioritize clarity, personality, and usefulness.
            Every sentence should feel intentional, not generated.
        IMPORTANT: Your response must be ONLY a valid JSON object with no additional text,
            explanations, or markdown formatting. Do not include any text before or after the JSON.
            ...
        """

    # ------------------------------------------------------------------
    # 7. LLM PROMPT — STEP 2: SECTIONS
    # ------------------------------------------------------------------
    def get_sections_prompt(self, content_data: dict) -> str:
        return f"""
            You are given the following data: {content_data}
            You are also provided with reference details in the format: "C001", "C002", etc., where each reference contains full bibliographic information including author names and publication year.

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
            - Include in-text author-year citations derived from the reference data. Use the following strict citation format rules:
                * 1 author:  (AuthorLastName, Year)  — e.g. (Hero, 2024)
                * 2 authors: (Author1LastName & Author2LastName, Year)  — e.g. (Smith & Jones, 2021)
                * 3 authors: (Author1LastName, Author2LastName & Author3LastName, Year)  — e.g. (Smith, Jones & Lee, 2019)
                * 4 or more authors: (FirstAuthorLastName et al., Year)  — e.g. (Smith et al., 2020)
            - The Introduction must contain exactly 10 paragraphs, each corresponding to one reference.
            - The citation marker must be placed at the end of the paragraph, immediately before the period, followed by two line breaks(\n).
            - Do NOT use numeric markers such as [1], [2], or "C001" style codes in the final text.

            Description
            - Word count: 500-700.
            - Include in-text author-year citations derived from the reference data. Apply the same strict citation format rules as above:
                * 1 author:  (AuthorLastName, Year)  — e.g. (Hero, 2024)
                * 2 authors: (Author1LastName & Author2LastName, Year)  — e.g. (Smith & Jones, 2021)
                * 3 authors: (Author1LastName, Author2LastName & Author3LastName, Year)  — e.g. (Smith, Jones & Lee, 2019)
                * 4 or more authors: (FirstAuthorLastName et al., Year)  — e.g. (Smith et al., 2020)
            - The Description must also contain exactly 10 paragraphs, each corresponding to one reference.
            - The citation marker must be placed at the end of the paragraph, immediately before the period, followed by two line breaks(\n).
            - Do NOT use numeric markers such as [1], [2], or "C001" style codes in the final text.

            Summary
            - Word count: 150-300.
            - Do not include citations (Strictly).
            - Focus on key points from the content in a concise manner.

            Abstract
            - Word count: 90-100.
            - Provide a brief summary of the content.
            - No citations required.

            Discussion
            - Word count: 200-400.
            - Include analysis, implications, or commentary derived from the content.
            - Citation markers can be included in ascending order, one per paragraph, placed at the end and before the period.

            Keywords
            - Extract 5-10 keywords directly from the content.
            - Keywords should be in Title Case and separated by comma(,).

            3. Writing Style
            - Formal academic tone.
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

        IMPORTANT: Respond with ONLY the title. The title should be in title case, all articles and joining words should be in lower case (Example: The Financial Literacy: Crucial for Outcomes and Resilience). No additional text, explanations, or formatting.
        """
