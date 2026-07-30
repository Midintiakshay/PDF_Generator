"""
base_template.py
----------------
Abstract base class that every journal template must inherit from.

Adding a new template
~~~~~~~~~~~~~~~~~~~~~
1. Create  Apps/template_configs/<my_brand>.py
2. Subclass BaseJournalTemplate
3. Set  brand_name  (must match the .tex filename, e.g. "myBrand.tex")
4. Implement the 3 abstract methods + the 3 prompt methods (see below)
5. Override any optional hooks that differ from defaults
6. Register it in  Apps/template_configs/factory.py

Every template file must define these 5 methods directly (no inheritance of defaults):
    get_references_prompt(journal)   — Step 1 LLM prompt
    get_sections_prompt(content_data)— Step 2 LLM prompt
    get_title_prompt(summary)        — Step 3 LLM prompt
    get_citation_format_prompt()     — inline citation format hint
    format_output_citation(...)      — final citation string
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date, timedelta


class BaseJournalTemplate(ABC):
    """
    Defines the contract every journal template must fulfil.

    Shared utilities (calendar math, HTML citation linking, etc.) have
    default implementations here.  Every prompt and citation style lives
    exclusively in the concrete template file — nothing is inherited.
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
        Override for weekday-only counting (e.g. alliedAcademy).
        """
        current_date = start_date + timedelta(days=days)
        while current_date.weekday() > 4:           # 5=Sat, 6=Sun
            current_date += timedelta(days=1)
        return current_date

    def format_volume_issue(self, volume: "int | str", issues: "int | str") -> "tuple[str, str]":
        """
        Format volume and issue numbers for the LaTeX template context.
        Default: zero-pad both values when they are a single digit (e.g. 4 → 04).
        Override in a brand template to apply different formatting rules.
        """
        v = f"0{volume}" if len(str(volume)) == 1 else str(volume)
        i = f"0{issues}" if len(str(issues)) == 1 else str(issues)
        return v, i

    # ------------------------------------------------------------------
    # 3. LLM CITATION FORMAT PROMPT  (abstract — must define in each file)
    # ------------------------------------------------------------------
    @abstractmethod
    def get_citation_format_prompt(self) -> str:
        """
        The inline citation format hint sent to the LLM.
        Used by PulsusInputStr.citeAuthorFormate.
        """

    # ------------------------------------------------------------------
    # 4. MANUSCRIPT NUMBER FORMATTING
    # ------------------------------------------------------------------
    def format_manuscript_numbers(self, manuscript_no: str) -> dict:
        """
        Default: all three fields equal the raw manuscriptNo.
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
        Override to add/remove/reorder sections for your brand.
        """
        return {
            "Introduction": forHtml.get("introduction", ""),
            "Description": forHtml.get("description", ""),
            "Conclusion": forHtml.get("conclusion", ""),
        }

    # ------------------------------------------------------------------
    # 7. IN-TEXT CITATION LINKING — HTML
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
    # 7b. IN-TEXT CITATION LINKING — LaTeX / PDF
    # ------------------------------------------------------------------
    def link_in_text_citations_pdf(self, forPdf: dict) -> dict:
        """
        Default: no transformation; LaTeX template handles [N] markers.
        Irjesti overrides this to substitute bold author-date markers.
        """
        return forPdf

    # ------------------------------------------------------------------
    # 8. HTML REFERENCE LIST ITEM
    # ------------------------------------------------------------------
    def render_html_reference(self, count: int, ref: dict) -> str:
        """
        Default <li> format.
        Override to change author format, punctuation, field order, etc.
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
    # 9. OUTPUT CITATION  (abstract — must define in each file)
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
        Formatted citation string used in the final PDF output.
        Each brand has its own citation style.
        """

    # ------------------------------------------------------------------
    # 10. MULTI-PASS PAGE-COUNT HOOK
    # ------------------------------------------------------------------
    #: Set to True in a brand template to trigger a 3rd xelatex compile
    #: after the total page count is known.  False for all other brands.
    needs_page_count_recompile: bool = False

    def build_pdf_no(self, page_count: int) -> str:
        """
        Given the total page count of the first-pass PDF, return the
        formatted ``pdfNo`` string to inject on the 3rd compile.

        Default returns the raw count as a string (no-op for brands that
        don't need a page range).  ABAcademies overrides this to return
        ``"1-{page_count}"``.
        """
        return str(page_count)

    # ------------------------------------------------------------------
    # 10. LATEX FONT CONFIGURATION
    # ------------------------------------------------------------------
    @property
    def latex_font(self) -> str:
        r"""
        LaTeX fontspec block for this brand's main font.
        Default is Times New Roman. Override in files that use a different typeface.
        """
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
    # 11–13. LLM PROMPTS  (abstract — must define in each template file)
    # ------------------------------------------------------------------
    @abstractmethod
    def get_references_prompt(self, journal) -> str:
        """
        Step-1 prompt: generate 10 structured references (C001-C010).
        Define the full prompt string in each template file.
        """

    @abstractmethod
    def get_sections_prompt(self, content_data: dict) -> str:
        """
        Step-2 prompt: turn references into intro/description/summary/abstract/discussion/keywords.
        Define the full prompt string in each template file.
        """

    @abstractmethod
    def get_title_prompt(self, summary: str) -> str:
        """
        Step-3 prompt: generate a short article title from the summary.
        Define the full prompt string in each template file.
        """
