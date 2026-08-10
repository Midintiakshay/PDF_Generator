"""
factory.py
----------
TemplateFactory — the single lookup point for template classes.

Usage
~~~~~
    from Apps.template_configs import TemplateFactory
    tmpl = TemplateFactory.get("alliedAcademy.tex")

Adding a new template
~~~~~~~~~~~~~~~~~~~~~
1.  Create  Apps/template_configs/<my_brand>.py  (subclass BaseJournalTemplate)
2.  Import it here and add one entry to _REGISTRY below.
    That's it — no changes to pipeline_service.py or models_journal.py needed.
"""

from __future__ import annotations
from .base_template import BaseJournalTemplate
from .allied_academy import AlliedAcademyTemplate
from .hilaris import HilarisTemplate
from .omics import OmicsTemplate
from .iomc import IomcTemplate
from .irjesti import IrjestiTemplate
from .ab_academies import ABAcademiesTemplate
from .interesjournal import InteresJournalTemplate
from .prime_scholars_library import PrimeScholarsLibraryTemplate
from .ejbi import EJBITemplate
from .jrmds import JrmdsTemplate
from .aabps import AabpsTemplate
from .jwhc import JwhcTemplate


# ---------------------------------------------------------------------------
# Registry: brand_name (str)  →  template instance (singleton-like)
# ---------------------------------------------------------------------------
_REGISTRY: dict[str, BaseJournalTemplate] = {
    "alliedAcademy.tex":  AlliedAcademyTemplate(),
    "hilaris.tex":        HilarisTemplate(),
    "omics.tex":          OmicsTemplate(),
    "iomc.tex":           IomcTemplate(),
    "Irjesti.tex":        IrjestiTemplate(),
    "ABAcademies.tex":    ABAcademiesTemplate(),
    "Interesjournal.tex": InteresJournalTemplate(),
    "PrimeScholarsLibrary.tex": PrimeScholarsLibraryTemplate(),
    "ejbi.tex":                EJBITemplate(),
    "jrmds.tex":               JrmdsTemplate(),
    "aabps.tex":               AabpsTemplate(),
    "jwhc.tex":                JwhcTemplate(),
}

# Lazy default (used when brand is unknown / new template in progress)
_DEFAULT_TEMPLATE = AlliedAcademyTemplate()


class TemplateFactory:
    @staticmethod
    def get(brand_name: str) -> BaseJournalTemplate:
        """
        Return the template instance for the given brand name.
        Falls back to the default template and prints a warning if brand is unknown.
        """
        template = _REGISTRY.get(brand_name)
        if template is None:
            print(
                f"[TemplateFactory] WARNING: Unknown brand '{brand_name}'. "
                "Falling back to default template. "
                "Create a new class in Apps/template_configs/ and register it in factory.py."
            )
            return _DEFAULT_TEMPLATE
        return template
