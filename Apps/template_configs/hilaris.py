"""
hilaris.py
----------
Template configuration for hilaris.tex
"""

from __future__ import annotations
from .base_template import BaseJournalTemplate


class HilarisTemplate(BaseJournalTemplate):
    brand_name = "hilaris.tex"
    date_intervals = [2, 14, 5, 7]     # calendar days (base default)

    # ------------------------------------------------------------------
    # 1. MANUSCRIPT NUMBER FORMATTING — unique Q-, P-, R- prefixes
    # ------------------------------------------------------------------
    def format_manuscript_numbers(self, manuscript_no: str) -> dict:
        base = manuscript_no.split("-")[-1]
        return {
            "QCNo": f"Q-{base}",
            "preQCNo": f"P-{base}",
            "RManuNo": f"R-{base}",
        }

    # ------------------------------------------------------------------
    # 2. LLM CITATION PROMPT
    # ------------------------------------------------------------------
    def get_citation_format_prompt(self) -> str:
        return (
            'author full names(there must be 3 to 6 authors and seperated with comma). '
            'title of that journal inside double quotation(" "). '
            'Journal short name Volume of the journal (year of publishing inside parenthesis):'
            'the page range or the number.end it with a full stop '
            "(for example: 'first author full name, second author full name, third author full name. "
            '"titleOFtheJournal." journalShortName Volume (year):ThePageRangeOrTheNumber.\')'
        )

    # ------------------------------------------------------------------
    # 3. HTML BODY SECTIONS — adds Acknowledgement + Conflict_of_Interest
    # ------------------------------------------------------------------
    def get_html_body_sections(self, forHtml: dict) -> dict:
        return {
            "Introduction": forHtml.get("introduction", ""),
            "Description": forHtml.get("description", ""),
            "Conclusion": forHtml.get("conclusion", ""),
            "Acknowledgement": None,
            "Conflict_of_Interest": None,
        }

    # ------------------------------------------------------------------
    # 4. HTML REFERENCE — uses full author names + italic journal name
    # ------------------------------------------------------------------
    def render_html_reference(self, count: int, ref: dict) -> str:
        title_query = "+".join(ref.get("title", "").split(" "))
        return (
            f'<li><a name="{count}" id="{count}"></a>'
            f'{ref.get("authors_full", "")}. '
            f'<a href="{ref.get("parentLink", "")}" target="_blank">"{ref.get("title", "")}"</a>.'
            f'<i>{ref.get("journalShortName", "")}</i> '
            f'{ref.get("volume", "")} ({ref.get("published", "")}):{ref.get("pageRangeOrNumber", "")}.'
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
        formatted = f"{parts[-1]}, {' '.join(parts[:-1])}"
        year = published.split("-")[-1]
        return f'{formatted}. "{title}." {short_journal} {volume} ({year}):{pdf_no}.'
