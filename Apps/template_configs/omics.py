"""
omics.py
--------
Template configuration for omics.tex
"""

from __future__ import annotations
from .base_template import BaseJournalTemplate


class OmicsTemplate(BaseJournalTemplate):
    brand_name = "omics.tex"
    date_intervals = [2, 14, 5, 7]

    # ------------------------------------------------------------------
    # 1. LLM CITATION PROMPT
    # ------------------------------------------------------------------
    def get_citation_format_prompt(self) -> str:
        return (
            "author names(first name + the remainings name's first letter"
            "(ex.: Arupa Nanda Swain then that should be Arupa NS) and there must be 3 to 6 authors"
            " and seperated with comma) (year of publishing inside parenthesis) "
            "title of that journal. Journal short name Volume of the journal:the page range or the number."
            "(for example: 'author n, author n, author n (year) titleOFtheJournal."
            " journalShortName Volume:ThePageRangeOrTheNumber')"
        )

    # ------------------------------------------------------------------
    # 2. HTML BODY SECTIONS — adds Abstract + Keywords
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
    # 3. HTML REFERENCE — author (year) title. journal volume:page
    # ------------------------------------------------------------------
    def render_html_reference(self, count: int, ref: dict) -> str:
        title_query = "+".join(ref.get("title", "").split(" "))
        return (
            f'<li><a name="{count}" id="{count}"></a>'
            f'{ref.get("authors_short", "")} ({ref.get("published", "")}) '
            f'<a href="{ref.get("parentLink", "")}" target="_blank">{ref.get("title", "")}</a>.'
            f'{ref.get("journalShortName", "")} {ref.get("volume", "")}:{ref.get("pageRangeOrNumber", "")}.'
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
        return f"{_fmt(author)} ({year}) {title}. {short_journal} {volume}: {pdf_no}."
