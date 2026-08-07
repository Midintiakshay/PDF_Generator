import os
import re
import copy
import subprocess
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# Need to make sure Apps is discoverable
import sys
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from Apps.testing.dummy_data import DUMMY_DATA
from Apps.template_configs import TemplateFactory
from Apps.language_fonts import LatexLanguageConfig
from Apps.models_journal import PulsusOutputStr

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "Apps" / "templates"
TESTING_DIR = PROJECT_ROOT / "Apps" / "testing"

def latex_escape(text):
    if not isinstance(text, str):
        return text
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "^": r"\^{}",
        "~": r"\textasciitilde{}",
        "\\": r"\textbackslash{}",
        "rizzBro": r"\textbf{",
        "hoez": r"}",
    }
    pattern = re.compile("|".join(re.escape(k) for k in replacements.keys()))
    return pattern.sub(lambda m: replacements[m.group()], text)

def run_test(template_name="ABAcademies.tex"):
    print(f"Testing template: {template_name}")
    
    # 1. Setup Jinja Environment
    env_latex = Environment(
        block_start_string=r"\BLOCK{",
        block_end_string="}",
        variable_start_string=r"\VAR{",
        variable_end_string="}",
        comment_start_string=r"\#{",
        comment_end_string="}",
        line_statement_prefix="%%",
        line_comment_prefix="%#",
        trim_blocks=True,
        autoescape=False,
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
    )
    env_latex.filters["latex_escape"] = latex_escape
    
    # 2. Get template
    try:
        latex_template = env_latex.get_template(template_name)
    except Exception as e:
        print(f"Error loading template {template_name}: {e}")
        return
        
    # 3. Render Template
    forPdf = copy.deepcopy(DUMMY_DATA)
    brand_name = template_name
    forPdf["brandName"] = brand_name
    
    try:
        pulsus_output = PulsusOutputStr(**forPdf)
        forPdf = pulsus_output.model_dump()
    except Exception as e:
        print(f"Warning: PulsusOutputStr model dump failed: {e}")
        template = TemplateFactory.get(brand_name)
        if "citation" not in forPdf or not forPdf["citation"]:
            forPdf["citation"] = template.format_output_citation(
                author=forPdf.get("author", ""),
                title=forPdf.get("title", ""),
                short_journal=forPdf.get("shortJournalName", ""),
                volume=forPdf.get("volume", ""),
                issues=forPdf.get("issues", ""),
                published=forPdf.get("published", ""),
                pdf_no=forPdf.get("pdfNo", ""),
            )
    
    # Generate dynamic fields via TemplateFactory
    template = TemplateFactory.get(brand_name)
    lang_map = LatexLanguageConfig().get_lang_map(template.latex_font)
    default_cfg = lang_map.get("default")
    
    preamble = (
        "\\usepackage{polyglossia}\n"
        + default_cfg["polyglossia"]
        + "\n"
        + default_cfg["font"]
    )
    forPdf["preamble"] = preamble
    forPdf["lang_name"] = "english"
    forPdf["lang"] = "en"
    
    # Process in-text citations if required by the template
    forPdf = template.link_in_text_citations_pdf(forPdf)
    
    try:
        rendered_latex = latex_template.render(**forPdf)
    except Exception as e:
        print(f"Error rendering template: {e}")
        return
        
    # 4. Save to file
    out_name = f"output_{template_name}"
    run_dir = TESTING_DIR / "dummy" / "test"
    run_dir.mkdir(parents=True, exist_ok=True)
    tex_file_path = run_dir / out_name
    tex_file_path.write_text(rendered_latex, encoding="utf-8")
    print(f"Rendered LaTeX saved to {tex_file_path}")
    
    # 5. Compile to PDF
    print("Compiling LaTeX to PDF...")
    for i in range(2):
        result = subprocess.run(
            [
                "xelatex",
                "-interaction=nonstopmode",
                tex_file_path.name,
            ],
            capture_output=True,
            text=True,
            cwd=run_dir, 
        )
        if result.returncode != 0:
            print(f"LaTeX compilation failed on run {i + 1}.")
            log_path = tex_file_path.with_suffix('.log')
            if log_path.exists():
                print(f"Check the log file: {log_path}")
            else:
                print("Error output:\n", result.stderr)
            return
            
    print(f"PDF successfully generated at {tex_file_path.with_suffix('.pdf')}")

if __name__ == "__main__":
    template_name = "ejbi.tex"
    run_test(template_name)
