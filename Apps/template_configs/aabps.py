from __future__ import annotations
from datetime import date, timedelta
from .base_template import BaseJournalTemplate

class AabpsTemplate(BaseJournalTemplate):
    brand_name = "aabps.tex"
    date_intervals = [2, 14, 5, 7]     # calendar days

    # ------------------------------------------------------------------
    # 0. DATE LOGIC — calendar days, skip weekends to Monday
    # ------------------------------------------------------------------
    def add_business_days(self, start_date: date, days: int) -> date:
        current_date = start_date + timedelta(days=days)
        while current_date.weekday() > 4:
            current_date += timedelta(days=1)
        return current_date

    # ------------------------------------------------------------------
    # 1. INLINE CITATION FORMAT PROMPT
    # ------------------------------------------------------------------
    def get_citation_format_prompt(self) -> str:
        return (
            "author names (Last name, First initial — max 6 authors, et al. for more) "
            "title of the article. Journal short name. year;Volume(Issue):the page range or the number. "
            "(for example: 'Smith J, Doe A. Impact of X. JournalShortName. 2022;15(3):200-215.')"
        )

    # ------------------------------------------------------------------
    # 2. HTML BODY SECTIONS
    # ------------------------------------------------------------------
    def get_html_body_sections(self, forHtml: dict) -> dict:
        return {
            "Abstract": forHtml.get("abstract", ""),
            "Keywords": forHtml.get("keywords", ""),
            "Introduction": forHtml.get("introduction", ""),
            "Description": forHtml.get("description", ""),
            "Conclusion": forHtml.get("conclusion", ""),
        }

    # ------------------------------------------------------------------
    # 3. LATEX FONT — Times New Roman
    # ------------------------------------------------------------------
    @property
    def latex_font(self) -> str:
        return r"""
        \usepackage{fontspec}
        \setmainfont{Times New Roman.ttf}[
            Path=../../../Fonts/,
            BoldFont=Times New Roman-Bold.ttf,
            ItalicFont=Times New Roman-Italic.ttf,
            BoldItalicFont=Times New Roman-BoldItalic.ttf
        ]"""

    # ------------------------------------------------------------------
    # 4. HTML REFERENCE
    # ------------------------------------------------------------------
    def render_html_reference(self, count: int, ref: dict) -> str:
        title_query = "+".join(ref.get("title", "").split(" "))
        return (
            f'<li><a name="{count}" id="{count}"></a>'
            f'{ref.get("authors_short", "")} '
            f'<a href="{ref.get("parentLink", "")}" target="_blank">{ref.get("title", "")}</a>. '
            f'<i>{ref.get("journalShortName", "")}</i>. {ref.get("published", "")};{ref.get("volume", "")}({ref.get("issues", "")}):{ref.get("pageRangeOrNumber", "")}.'
            f'</li>'
        )

    # ------------------------------------------------------------------
    # 5. OUTPUT CITATION
    # ------------------------------------------------------------------
    def format_output_citation(self, author, title, short_journal, volume, issues, published, pdf_no) -> str:
        year = published.split("-")[-1] if "-" in published else published
        if year.isdigit() and len(published) > 4:
            year = published.split("-")[0] if len(published.split("-")[0]) == 4 else year
        return f"{author}. {title}. {short_journal}. {year};{volume}({issues}):{pdf_no}"

    # ------------------------------------------------------------------
    # 6. LLM PROMPT — STEP 1: REFERENCES
    # ------------------------------------------------------------------
    def get_references_prompt(self, journal) -> str:
        return f"""
        You are provided by a topic:
        topic : "{journal.topic}"
        journal name: "{journal.journalName}"
        depart
        
        
        ment: "{journal.authorsDepartment}" ignore the university name if mentioned. use the department name only as reference.
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
            "published": "...", # Just the Year is preferred
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
                "introduction": "Text for the first paragraph [1].\\n\\nText for the second paragraph [2].\\n\\n(continue for all 10 paragraphs...)",
                "description": "Text for the first paragraph [1].\\n\\nText for the second paragraph [2].\\n\\n(continue for all 10 paragraphs...)",
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
            - MUST INCLUDE exactly 10 paragraphs, each corresponding to one reference.
            - You MUST map the reference IDs to numbered citations: "C001" becomes [1], "C002" becomes [2], and so on up to [10].
            - MUST INCLUDE exactly one citation marker per paragraph, in sequential order: [1] in the first paragraph, [2] in the second, ..., [10] in the tenth.
            - CRITICAL: DO NOT use citations in the middle of sentences. The citation marker MUST be placed at the VERY END of the paragraph, immediately before the final period, exactly like this: "last sentence of the paragraph [1]." followed by two line breaks(\\n).

            Description
            - Word count: 500-700.
            - MUST INCLUDE exactly 10 paragraphs, each corresponding to one reference.
            - You MUST map the reference IDs to numbered citations: "C001" becomes [1], "C002" becomes [2], and so on up to [10].
            - MUST INCLUDE exactly one citation marker per paragraph, in sequential order: [1] in the first paragraph, [2] in the second, ..., [10] in the tenth.
            - CRITICAL: DO NOT use citations in the middle of sentences. The citation marker MUST be placed at the VERY END of the paragraph, immediately before the final period, exactly like this: "last sentence of the paragraph [2]." followed by two line breaks(\\n).

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
    # 8. LLM PROMPT — STEP 3: TITLE
    # ------------------------------------------------------------------
    def format_title(self, generated_title: str) -> str:
        return generated_title.strip().capitalize()

    def get_title_prompt(self, summary: str) -> str:
        return f"""
        Generate a 5-7 word title based on this summary: {summary}

        IMPORTANT: Respond with ONLY the title. The title should be in sentence case. No additional text, explanations, or formatting.
        """
