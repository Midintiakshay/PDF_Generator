"""
base_template.py
----------------
Abstract base class that every journal template must inherit from.

Adding a new template
~~~~~~~~~~~~~~~~~~~~~
1. Create a new file  Apps/template_configs/<my_brand>.py
2. Subclass BaseJournalTemplate
3. Set class-level brand_name  (must match the .tex filename, e.g. "myBrand.tex")
4. Override only the methods whose behaviour differs from the defaults below
5. Register it in  Apps/template_configs/factory.py
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date, timedelta


class BaseJournalTemplate(ABC):
    """
    Defines the contract every journal template must fulfil.

    Defaults implement the most common behaviour (calendar-day counting,
    numeric in-text citations, a simple reference <li>, etc.).
    Subclasses only need to override what is different for their brand.
    """

    # ------------------------------------------------------------------
    # 1. IDENTITY
    # ------------------------------------------------------------------
    #: Must match the .tex filename exactly, e.g. "alliedAcademy.tex"
    brand_name: str

    # ------------------------------------------------------------------
    # 2. DATE LOGIC
    # ------------------------------------------------------------------
    #: Days for each workflow stage [editor_assign, review, revise, publish]
    date_intervals: list[int] = [2, 14, 5, 7]

    def add_business_days(self, start_date: date, days: int) -> date:
        """
        Default: add calendar days; if landing on Sat/Sun, move to Monday.
        Override this method for weekday-only counting (e.g. alliedAcademy).
        """
        current_date = start_date + timedelta(days=days)
        while current_date.weekday() > 4:           # 5=Sat, 6=Sun
            current_date += timedelta(days=1)
        return current_date

    # ------------------------------------------------------------------
    # 3. LLM CITATION PROMPT
    # ------------------------------------------------------------------
    @abstractmethod
    def get_citation_format_prompt(self) -> str:
        """
        Returns the natural-language prompt snippet that instructs the LLM
        how to format citations for this journal brand.
        This is used by PulsusInputStr.citeAuthorFormate.
        """

    # ------------------------------------------------------------------
    # 4. MANUSCRIPT NUMBER FORMATTING
    # ------------------------------------------------------------------
    def format_manuscript_numbers(self, manuscript_no: str) -> dict:
        """
        Default: all three number fields are identical to the raw manuscriptNo.
        hilaris.tex overrides this to add Q-, P-, R- prefixes.
        """
        return {
            "QCNo": manuscript_no,
            "preQCNo": manuscript_no,
            "RManuNo": manuscript_no,
        }

    # ------------------------------------------------------------------
    # 5. TITLE FORMATTING (post LLM generation)
    # ------------------------------------------------------------------
    def format_title(self, generated_title: str) -> str:
        """
        Default: strip surrounding whitespace only.
        alliedAcademy overrides this to apply sentence-case rules.
        """
        return generated_title.strip()

    # ------------------------------------------------------------------
    # 6. HTML BODY SECTIONS
    # ------------------------------------------------------------------
    def get_html_body_sections(self, forHtml: dict) -> dict:
        """
        Default sections rendered in the HTML output.
        Returns an ordered dict of {SectionLabel: content_string | None}.
        None values are rendered as empty placeholders.
        Override to add/remove/reorder sections for your brand.
        """
        return {
            "Introduction": forHtml.get("introduction", ""),
            "Description": forHtml.get("description", ""),
            "Conclusion": forHtml.get("conclusion", ""),
        }

    # ------------------------------------------------------------------
    # 7. IN-TEXT CITATION LINKING  (for HTML output)
    # ------------------------------------------------------------------
    def link_in_text_citations_html(self, forHtml: dict) -> dict:
        """
        Default: replace [N]. with a numeric hyperlink anchor.
        Irjesti overrides this to use author-date format.
        """
        for i in range(1, len(forHtml.get("content", {})) + 1):
            link = f'[<a href="#{i}" title="{i}">{i}</a>].</p><p>'
            for field in ("introduction", "description", "discussion", "abstract", "conclusion"):
                if field in forHtml:
                    forHtml[field] = forHtml[field].replace(f"[{i}].", link)
        return forHtml

    # ------------------------------------------------------------------
    # 7b. IN-TEXT CITATION LINKING  (for LaTeX/PDF output)
    # ------------------------------------------------------------------
    def link_in_text_citations_pdf(self, forPdf: dict) -> dict:
        """
        Default: no transformation needed; LaTeX template handles [N] markers.
        Irjesti overrides this to substitute bold author-date markers.
        """
        return forPdf

    # ------------------------------------------------------------------
    # 8. HTML REFERENCE LIST ITEM
    # ------------------------------------------------------------------
    def render_html_reference(self, count: int, ref: dict) -> str:
        """
        Default reference <li> format (alliedAcademy / fallback style).
        Override to change author name usage (short vs full), punctuation,
        field order, etc.
        """
        title_query = "+".join(ref.get("title", "").split(" "))
        return (
            f'<li><a name="{count}" id="{count}"></a>'
            f'{ref.get("authors_short", "")}. '
            f'<a href="{ref.get("parentLink", "")}" target="_blank">{ref.get("title", "")}</a>. '
            f'{ref.get("journalShortName", "")}. '
            f'{ref.get("published", "")};{ref.get("volume", "")}{ref.get("issues", "")}:{ref.get("pageRangeOrNumber", "")}.'
            f'<p align="right">'
            f'<a href="{ref.get("url", "")}" target="_blank"><u>Indexed at</u></a>, '
            f'<a href="https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5&q={title_query}&btnG=" target="_blank"><u>Google Scholar</u></a>, '
            f'<a href="https://doi.org/{ref.get("DOI", "")}" target="_blank"><u>Crossref</u></a>'
            f'</p></li>'
        )

    # ------------------------------------------------------------------
    # 9. OUTPUT CITATION (PulsusOutputStr.citation computed field)
    # ------------------------------------------------------------------
    @abstractmethod
    def format_output_citation(
        self,
        author: str,
        title: str,
        short_journal: str,
        volume: str,
        issues: str,
        published: str,
        pdf_no: int,
    ) -> str:
        """
        Returns the formatted citation string used in the final PDF output.
        Each brand has its own citation style (Chicago, APA-like, custom).
        """
