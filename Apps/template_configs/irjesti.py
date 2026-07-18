"""
irjesti.py
----------
Template configuration for Irjesti.tex

Self-contained: all prompts, font, and layout defined here.
"""

from __future__ import annotations
from .base_template import BaseJournalTemplate


class IrjestiTemplate(BaseJournalTemplate):
    brand_name = "Irjesti.tex"
    date_intervals = [2, 14, 5, 7]

    # ------------------------------------------------------------------
    # 1. INLINE CITATION FORMAT PROMPT
    # ------------------------------------------------------------------
    def get_citation_format_prompt(self) -> str:
        return (
            "author names (Last name, First initial — max 6 authors, et al. for more) "
            "year. title of article. journal short name, volume(issue), page range or article number. "
            "DOI. "
            "(for example: 'Smith J, Doe A, Lee B 2022. Impact of X on Y. "
            "JournalShortName, 15(3), 200-215. https://doi.org/...')"
        )

    # ------------------------------------------------------------------
    # 2. HTML BODY SECTIONS — includes Discussion
    # ------------------------------------------------------------------
    def get_html_body_sections(self, forHtml: dict) -> dict:
        return {
            "Introduction": forHtml.get("introduction", ""),
            "Description": forHtml.get("description", ""),
            "Discussion": forHtml.get("discussion", ""),
            "Conclusion": forHtml.get("conclusion", ""),
        }

    # ------------------------------------------------------------------
    # 3. LATEX FONT — Calibri (unique to Irjesti)
    # ------------------------------------------------------------------
    @property
    def latex_font(self) -> str:
        return r"""
        \usepackage{fontspec}
        \setmainfont{Calibri}[
            Path=../../../Fonts/,
            UprightFont    = *-Regular ,
            BoldFont       = *-Bold ,
            ItalicFont     = *-Italic ,
            BoldItalicFont = *-BoldItalic
        ]"""

    # ------------------------------------------------------------------
    # 4. IN-TEXT CITATION LINKING (HTML) — author-date format
    # ------------------------------------------------------------------
    def link_in_text_citations_html(self, forHtml: dict) -> dict:
        content = forHtml.get("content", {})
        keys = list(content.keys())
        for i, key in enumerate(keys, start=1):
            ref = content.get(key, {})
            authors_list = ref.get("authors", [])
            year = ref.get("published", "").split("-")[0]
            if authors_list:
                last_name = authors_list[0].split(" ")[-1]
                author_date = f"{last_name} et al., {year}" if len(authors_list) > 1 else f"{last_name}, {year}"
            else:
                author_date = str(i)
            link = f'[<a href="#{i}" title="{author_date}">{author_date}</a>].</p><p>'
            for field in ("introduction", "description", "discussion", "abstract", "conclusion"):
                if field in forHtml:
                    forHtml[field] = forHtml[field].replace(f"[{i}].", link)
        return forHtml

    # ------------------------------------------------------------------
    # 4b. IN-TEXT CITATION LINKING (PDF) — bold author-date markers
    # ------------------------------------------------------------------
    def link_in_text_citations_pdf(self, forPdf: dict) -> dict:
        content = forPdf.get("content", {})
        keys = list(content.keys())
        for i, key in enumerate(keys, start=1):
            ref = content.get(key, {})
            authors_list = ref.get("authors", [])
            year = ref.get("published", "").split("-")[0]
            if authors_list:
                last_name = authors_list[0].split(" ")[-1]
                author_date = f"{last_name} et al., {year}" if len(authors_list) > 1 else f"{last_name}, {year}"
            else:
                author_date = str(i)
            bold_marker = f"\\textbf{{[{author_date}]}}"
            for field in ("introduction", "description", "discussion", "abstract", "conclusion"):
                if field in forPdf:
                    forPdf[field] = forPdf[field].replace(f"[{i}]", bold_marker)
        return forPdf

    # ------------------------------------------------------------------
    # 5. HTML REFERENCE — author (year). title. italic journal, vol(iss):page
    # ------------------------------------------------------------------
    def render_html_reference(self, count: int, ref: dict) -> str:
        title_query = "+".join(ref.get("title", "").split(" "))
        authors_list = ref.get("authors", [])
        year = ref.get("published", "").split("-")[0]
        if authors_list:
            last_name = authors_list[0].split(" ")[-1]
            author_date = f"{last_name} et al. {year}." if len(authors_list) > 1 else f"{last_name}. {year}."
        else:
            author_date = ""
        return (
            f'<li><a name="{count}" id="{count}"></a>'
            f'{author_date} '
            f'<a href="{ref.get("parentLink", "")}" target="_blank">{ref.get("title", "")}</a>.'
            f'<i>{ref.get("journalShortName", "")}</i>, '
            f'{ref.get("volume", "")}({ref.get("issues", "")}):{ref.get("pageRangeOrNumber", "")}.'
            f'<p align="right">'
            f'<a href="{ref.get("url", "")}" target="_blank"><u>Indexed at</u></a>, '
            f'<a href="https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5&q={title_query}&btnG=" target="_blank"><u>Google Scholar</u></a>, '
            f'<a href="https://doi.org/{ref.get("DOI", "")}" target="_blank"><u>Crossref</u></a>'
            f'</p></li>'
        )

    # ------------------------------------------------------------------
    # 6. OUTPUT CITATION
    # ------------------------------------------------------------------
    def format_output_citation(self, author, title, short_journal, volume, issues, published, pdf_no) -> str:
        parts = author.split(" ")
        year = published.split("-")[0]
        last = parts[-1]
        first_initial = parts[0][0] if parts else ""
        return f"{last} {first_initial} {year}. {title}. {short_journal}, {volume}({issues}): {pdf_no}."

    # ------------------------------------------------------------------
    # 7. LLM PROMPT — STEP 1: REFERENCES
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
    # 8. LLM PROMPT — STEP 2: SECTIONS
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
            - Include sequential citation markers from the references: "C001" -> [1], "C002" -> [2], and so on.
            - The Introduction must contain exactly 10 paragraphs, each corresponding to one reference.
            - The citation marker must be placed at the end of the paragraph, immediately before the period, followed by two line breaks(\n).

            Description
            - Word count: 500-700.
            - Include sequential citation markers: "C001" -> [1], "C002" -> [2], and so on.
            - The Description must also contain exactly 10 paragraphs, each corresponding to one reference.
            - The citation marker must be placed at the end of the paragraph, immediately before the period, followed by two line breaks(\n).

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
            - Keywords should be in Title Case and separated by semi-colon(;).

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
    # 9. LLM PROMPT — STEP 3: TITLE
    # ------------------------------------------------------------------
    def get_title_prompt(self, summary: str) -> str:
        return f"""
        Generate a 5-7 word title based on this summary: {summary}

        IMPORTANT: Respond with ONLY the title. The title should be in title case, all articles and joining words should be in lower case (Example: The Financial Literacy: Crucial for Outcomes and Resilience). No additional text, explanations, or formatting.
        """
