# How to Create a New Journal Template

This document provides a comprehensive guide on how to add a new journal template to the PDF Generator pipeline.

The pipeline uses an Object-Oriented **Strategy Pattern**. Each journal brand (e.g., *Allied Academy*, *Hilaris*) has its own self-contained Python file that defines all its specific rules: font styles, citation formats, layout sections, LLM prompts, and date calculations.

## Overview

To add a new template, you only need to do two things:
1. Create a new `.py` file in `Apps/template_configs/` that subclasses `BaseJournalTemplate`.
2. Register your new class in `Apps/template_configs/factory.py`.

No core pipeline files (`pipeline_service.py`, `language_fonts.py`) need to be modified.

---

## Step 1: Create the File

Create a new Python file in `Apps/template_configs/`, for example `my_new_brand.py`.

Import the base class and set up your template:

```python
from __future__ import annotations
from datetime import date, timedelta
from .base_template import BaseJournalTemplate

class MyNewBrandTemplate(BaseJournalTemplate):
    # Must match the exact .tex filename used by the journal
    brand_name = "myNewBrand.tex"
```

---

## Step 2: Date Logic

By default, the base class calculates target dates by adding simple calendar days (skipping weekends if they land exactly on a Saturday/Sunday).

If your journal requires a different timeline (e.g., only counting business days, or different intervals for review/publish), override these:

```python
    # Days for: [editor_assign, review, revise, publish]
    date_intervals = [2, 14, 5, 7]

    # Optional: Override if you only count Mon-Fri
    def add_business_days(self, start_date: date, days: int) -> date:
        current_date = start_date
        added_days = 0
        while added_days < days:
            current_date += timedelta(days=1)
            if current_date.weekday() < 5:  # Mon-Fri
                added_days += 1
        return current_date
```

---

## Step 3: LaTeX Font Configuration

Define the exact LaTeX font block that should be injected into the generated `.tex` file.

```python
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
```

---

## Step 4: HTML Body Sections

Define which sections should appear in the generated HTML and in what order. The base template provides Introduction, Description, and Conclusion. You can add sections like `Abstract`, `Keywords`, `Discussion`, `Acknowledgement`, etc.

```python
    def get_html_body_sections(self, forHtml: dict) -> dict:
        return {
            "Abstract": forHtml.get("abstract", ""),
            "Keywords": forHtml.get("keywords", ""),
            "Introduction": forHtml.get("introduction", ""),
            "Description": forHtml.get("description", ""),
            "Conclusion": forHtml.get("conclusion", ""),
            "Acknowledgement": None, # Renders as an empty placeholder if None
        }
```

---

## Step 5: Formatting Hooks (Optional)

You can override how manuscript numbers and titles are formatted before they hit the template.

### A. Manuscript Numbers
By default, the `QCNo`, `preQCNo`, and `RManuNo` are all exactly equal to the base `manuscript_no`. If your journal adds prefixes (like `Q-` or `P-`), override this:

```python
    def format_manuscript_numbers(self, manuscript_no: str) -> dict:
        return {
            "QCNo": f"Q-{manuscript_no}",
            "preQCNo": f"P-{manuscript_no}",
            "RManuNo": f"R-{manuscript_no}",
        }
```

### B. Title Formatting
If your journal enforces specific casing for titles (e.g., Sentence Case), override this hook:

```python
    def format_title(self, generated_title: str) -> str:
        # e.g., Allied Academies enforces sentence case
        return generated_title.strip().capitalize()
```

---

## Step 6: Citations and References

Journals have wildly different citation styles. You must define how citations are requested from the LLM, how they are rendered in HTML, and how they appear in the final PDF.

### A. The LLM Format Prompt
This is the instruction sent to the LLM when generating references.

```python
    def get_citation_format_prompt(self) -> str:
        return (
            "author names (Last name, First initial — max 6 authors, et al. for more) "
            "year. title of article. journal short name, volume(issue), page range. "
            "(for example: 'Smith J, Doe A 2022. Impact of X. JournalShortName, 15(3), 200-215.')"
        )
```

### B. The Final Output Citation (PDF)
How the citation should look in the final PDF metadata string.

```python
    def format_output_citation(self, author, title, short_journal, volume, issues, published, pdf_no) -> str:
        year = published.split("-")[0]
        return f"{author} {year}. {title}. {short_journal}, {volume}({issues}): {pdf_no}."
```

### C. The HTML Reference List Item
How the `<li>` element is rendered in the HTML version of the document.

```python
    def render_html_reference(self, count: int, ref: dict) -> str:
        title_query = "+".join(ref.get("title", "").split(" "))
        return (
            f'<li><a name="{count}" id="{count}"></a>'
            f'{ref.get("authors_short", "")} ({ref.get("published", "")}). '
            f'<a href="{ref.get("url", "")}" target="_blank">"{ref.get("title", "")}"</a>.'
            f'<i>{ref.get("journalShortName", "")}</i>, '
            f'{ref.get("volume", "")}({ref.get("issues", "")}), {ref.get("pageRangeOrNumber", "")}.'
            f'</li>'
        )
```

### D. In-Text Citation Linking (Optional)
If your journal uses `[1]` format, the base class handles this automatically. If your journal uses Author-Date markers (e.g., `[Smith et al., 2022]`), you can override these hooks:

- `link_in_text_citations_html(self, forHtml: dict) -> dict`
- `link_in_text_citations_pdf(self, forPdf: dict) -> dict`

*(See `irjesti.py` for a complete example of Author-Date linking).*

---

## Step 7: The 3 Core LLM Prompts

Every template **must** define its own prompts for generating the article content. This ensures no template accidentally inherits a prompt that breaks its specific layout requirements.

These methods are strictly required. You can usually copy/paste these from an existing template (like `omics.py`) and tweak the word counts or section requirements as needed.

### 1. The References Prompt
Generates the initial 10 references (`C001-C010`) and summary.

```python
    def get_references_prompt(self, journal) -> str:
        return f"""
        You are provided by a topic:
        topic : "{journal.topic}"
        journal name: "{journal.journalName}"
        ...
        (Copy the full prompt body from another template and modify as needed)
        """
```

### 2. The Sections Prompt
Turns the raw references into full paragraphs (Introduction, Description, etc.).

```python
    def get_sections_prompt(self, content_data: dict) -> str:
        return f"""
        You are given the following data: {content_data}
        ...
        (Copy the full prompt body from another template and modify word counts)
        """
```

### 3. The Title Prompt
Generates the 5-7 word title.

```python
    def get_title_prompt(self, summary: str) -> str:
        return f"""
        Generate a 5-7 word title based on this summary: {summary}
        ...
        """
```

---

## Step 8: Registration

Once your `my_new_brand.py` file is complete, you must register it in the factory so the pipeline knows it exists.

Open `Apps/template_configs/factory.py`:

```python
# 1. Import your new class
from .my_new_brand import MyNewBrandTemplate

class TemplateFactory:
    _templates = {
        # ... existing templates ...
        
        # 2. Add your brand
        "myNewBrand.tex": MyNewBrandTemplate(),
    }
```

That's it! The system will now route all traffic for `myNewBrand.tex` through your new class, completely isolated from the rest of the application.
