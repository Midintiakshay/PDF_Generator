"""
irjesti.py
----------
Template configuration for Irjesti.tex

Key uniqueness:
- Author-date in-text citations  ([Smith et al., 2023]  instead of [1])
- Both HTML and PDF need different substitution logic
"""

from __future__ import annotations
from .base_template import BaseJournalTemplate


class IrjestiTemplate(BaseJournalTemplate):
    brand_name = "Irjesti.tex"
    date_intervals = [2, 14, 5, 7]

    # ------------------------------------------------------------------
    # 1. LLM CITATION PROMPT
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
    # 3. IN-TEXT CITATION LINKING (HTML) — author-date format
    # ------------------------------------------------------------------
    def link_in_text_citations_html(self, forHtml: dict) -> dict:
        start = 0
        for key in forHtml.get("content", {}).keys():
            start += 1
            ref = forHtml["content"][key]
            first_author = ref.get("authors_short", "").split(", ")[0]
            year = ref.get("published", "")
            label = f"[{first_author} et al., {year}]"
            anchor = f'[<a href="#{start}" title="{start}">{label}</a>].</p><p>'
            for field in ("introduction", "description", "discussion"):
                if field in forHtml:
                    forHtml[field] = forHtml[field].replace(f"[{start}].", anchor)
        return forHtml

    # ------------------------------------------------------------------
    # 4. IN-TEXT CITATION LINKING (PDF/LaTeX) — bold author-date format
    # ------------------------------------------------------------------
    def link_in_text_citations_pdf(self, forPdf: dict) -> dict:
        start = 0
        for key in forPdf.get("content", {}).keys():
            start += 1
            ref = forPdf["content"][key]
            first_author = ref.get("authors_short", "").split(", ")[0]
            year = ref.get("published", "")
            # rizzBro / hoez are LaTeX bold markers (expanded by latex_escape filter)
            bold_label = f"rizzBro({first_author} et al., {year}).hoez"
            for field in ("introduction", "description", "discussion"):
                if field in forPdf:
                    forPdf[field] = forPdf[field].replace(f"[{start}].", bold_label)
        return forPdf

    # ------------------------------------------------------------------
    # 5. HTML REFERENCE — default style (same as alliedAcademy)
    # ------------------------------------------------------------------
    # No override needed — inherits BaseJournalTemplate.render_html_reference

    # ------------------------------------------------------------------
    # 6. OUTPUT CITATION
    # ------------------------------------------------------------------
    def format_output_citation(self, author, title, short_journal, volume, issues, published, pdf_no) -> str:
        def _fmt(name: str) -> str:
            parts = name.split(" ")
            initials = "".join(p[0] for p in parts[:-1])
            return f"{parts[-1]} {initials}"
        year = published.split("-")[-1]
        return f"{_fmt(author)},({year}) {title}. {short_journal} {volume}: {pdf_no}."
