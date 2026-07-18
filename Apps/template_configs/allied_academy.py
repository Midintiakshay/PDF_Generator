"""
allied_academy.py
-----------------
Template configuration for alliedAcademy.tex
"""

from __future__ import annotations
from datetime import date, timedelta
from .base_template import BaseJournalTemplate


class AlliedAcademyTemplate(BaseJournalTemplate):
    brand_name = "alliedAcademy.tex"

    # ------------------------------------------------------------------
    # 1. DATE LOGIC — weekdays only
    # ------------------------------------------------------------------
    date_intervals = [2, 14, 7, 7]

    def add_business_days(self, start_date: date, days: int) -> date:
        current_date = start_date
        added_days = 0
        while added_days < days:
            current_date += timedelta(days=1)
            if current_date.weekday() < 5:          # Mon-Fri
                added_days += 1
        return current_date

    # ------------------------------------------------------------------
    # 2. LLM CITATION PROMPT
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
    # 3. TITLE FORMATTING — sentence-case per colon segment
    # ------------------------------------------------------------------
    def format_title(self, generated_title: str) -> str:
        parts = generated_title.strip().split(": ")
        if len(parts) == 1:
            return parts[0].capitalize()
        return ": ".join(part.capitalize() for part in parts)

    # ------------------------------------------------------------------
    # 4. HTML BODY SECTIONS
    # ------------------------------------------------------------------
    def get_html_body_sections(self, forHtml: dict) -> dict:
        return {
            "Introduction": forHtml.get("introduction", ""),
            "Conclusion": forHtml.get("conclusion", ""),
        }

    # ------------------------------------------------------------------
    # 5. OUTPUT CITATION
    # ------------------------------------------------------------------
    def format_output_citation(self, author, title, short_journal, volume, issues, published, pdf_no) -> str:
        def _fmt(name: str) -> str:
            parts = name.split(" ")
            initials = "".join(p[0] for p in parts[:-1])
            return f"{parts[-1]} {initials}"
        year = published.split("-")[-1]
        return f"{_fmt(author)}. {title}. {short_journal}. {year};{volume}({issues}):{pdf_no}."
