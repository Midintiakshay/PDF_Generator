"""
rroj.py
--------
Template configuration for rroj.tex
"""

from __future__ import annotations
from .base_template import BaseJournalTemplate

class RrojTemplate(BaseJournalTemplate):
    brand_name = "rroj.tex"

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

    def get_citation_format_prompt(self) -> str:
        return (
            "author names(first name + the remainings name's first letter"
            "(ex.: Arupa Nanda Swain then that should be Arupa NS) and there must be 3 to 6 authors"
            " and seperated with comma) (year of publishing inside parenthesis) "
            "title of that journal. Journal short name Volume of the journal:the page range or the number."
        )

    def format_output_citation(self, author, title, short_journal, volume, issues, published, pdf_no) -> str:
        year = published.split("-")[-1] if published else ""
        return f"{author} ({year}) {title}. {short_journal} {volume}: {pdf_no}."

    def get_references_prompt(self, journal) -> str:
        return "Generate references..."

    def get_sections_prompt(self, content_data: dict) -> str:
        return "Generate sections..."

    def get_title_prompt(self, summary: str) -> str:
        return "Generate title..."
