"""
iomc.py
-------
Template configuration for iomc.tex
"""

from __future__ import annotations
from .base_template import BaseJournalTemplate


class IomcTemplate(BaseJournalTemplate):
    brand_name = "iomc.tex"
    date_intervals = [2, 14, 5, 7]

    # ------------------------------------------------------------------
    # 1. LLM CITATION PROMPT  (defaults to alliedAcademy-style)
    # ------------------------------------------------------------------
    def get_citation_format_prompt(self) -> str:
        return (
            "author names(first name + the remainings name's first letter"
            "(ex.: Arupa Nanda Swain then that should be Arupa NS) and there must be 3 or less,"
            " not more authors then that and seperated with comma). "
            "title of that journal. Journal short name. year of publishing;"
            "Volume of the journal:the page range or the number."
            "(for example: 'author n, author n, author n. titleOFtheJournal."
            " journalShortName. year;Volume:ThePageRangeOrTheNumber.')"
        )

    # ------------------------------------------------------------------
    # 2. HTML BODY SECTIONS
    # ------------------------------------------------------------------
    def get_html_body_sections(self, forHtml: dict) -> dict:
        return {
            "Introduction": forHtml.get("introduction", ""),
            "Description": forHtml.get("description", ""),
            "Conclusion": forHtml.get("conclusion", ""),
        }

    # ------------------------------------------------------------------
    # 3. HTML REFERENCE — italic journal, url used for both Indexed+title
    # ------------------------------------------------------------------
    def render_html_reference(self, count: int, ref: dict) -> str:
        title_query = "+".join(ref.get("title", "").split(" "))
        return (
            f'<li><a name="{count}" id="{count}"></a>'
            f'{ref.get("authors_short", "")} '
            f'<a href="{ref.get("url", "")}" target="_blank">"{ref.get("title", "")}"</a>.'
            f'<i>{ref.get("journalShortName", "")}</i> '
            f'({ref.get("published", "")});{ref.get("volume", "")}:{ref.get("pageRangeOrNumber", "")}.'
            f'<p align="right">'
            f'<a href="{ref.get("url", "")}" target="_blank"><u>Indexed at</u></a>, '
            f'<a href="https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5&q={title_query}&btnG=" target="_blank"><u>Google Scholar</u></a>, '
            f'<a href="https://doi.org/{ref.get("DOI", "")}" target="_blank"><u>Crossref</u></a>'
            f'</p></li>'
        )

    # ------------------------------------------------------------------
    # 4. OUTPUT CITATION
    # ------------------------------------------------------------------
    def format_output_citation(self, author, title, short_journal, volume, issues, published, pdf_no) -> str:
        def _fmt(name: str) -> str:
            parts = name.split(" ")
            initials = "".join(p[0] for p in parts[:-1])
            return f"{parts[-1]} {initials}"
        year = published.split("-")[-1]
        return f"{_fmt(author)}, {title}. {short_journal}({year}) {volume}: {pdf_no}."
