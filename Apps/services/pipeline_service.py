from Apps.config import Config
from Apps.services.io_service import IOService
from Apps.models_journal import PulsusInputStr, PulsusOutputStr
from Apps.language_fonts import LatexLanguageConfig
from Apps.library_import import *
from Apps.library_import import pathOfPathLib
from Apps.template_configs import TemplateFactory
import threading
import time as _time

# ---------------------------------------------------------------------------
# Debug helpers
# ---------------------------------------------------------------------------

def _dbg(journal_id: str, msg: str, t0: float | None = None) -> None:
    """
    Print a timestamped debug line.
    If t0 is supplied, also prints the elapsed seconds since that checkpoint.
    Format: [HH:MM:SS.mmm] [thread-name] [journal_id] | msg  (+X.XXs)
    """
    ts   = _time.strftime("%H:%M:%S", _time.localtime()) + f".{int(_time.time() * 1000) % 1000:03d}"
    thr  = threading.current_thread().name
    elap = f"  (+{_time.time() - t0:.2f}s)" if t0 is not None else ""
    print(f"[{ts}] [{thr}] [{journal_id}] | {msg}{elap}")


class PipelineService:
    """
    Handles the complete pipeline for journal processing and PDF generation.
    """

    gemClient, GroqClient, CORE_API_KEY = Config.init_clients()

    @staticmethod
    async def process_journal(journal: PulsusInputStr):
        """
        Full journal pipeline:
        1. Save input
        2. Generate content using Gemini
        3. Parse + clean content
        4. Generate PDF & HTML
        5. Return JSON status
        """
        # ---------- Step 1: Validate input (do NOT write to DB yet) ----------
        IOService.INPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = IOService.fetchInputData()
        journal.id = journal.id.strip()
        journal.author = journal.author.strip()
        if journal.id in data:
            raise HTTPException(status_code=400, detail="Journal ID already exists.")
        data[journal.id] = journal.model_dump(exclude=["id"])
        print("Step 1 : Validated journal input (DB write deferred until PDF success) ✔")

        # ---------- Step 2: Build LLM Prompt ----------
        prompt = PipelineService._build_prompt(journal)
        print("Step 2 : Created universal prompt ✔")

        # ---------- Step 3: Ask Gemini ----------
        # gem_summary = PipelineService._ask_gemini_with_retries(prompt)
        # print("Step 3 : Gemini response received ✔")

        # ---------- Step 3,4: Meta data Parse LLM JSON ----------
        content_data = PipelineService._parse_gemini_response(prompt)
        print("Step 3,4 : Generation with Parsing the structured JSON ✔")

        # ---------- Step 5: Create title, abstract, summary ----------
        processed_sections = PipelineService._process_sections(content_data, journal)
        processed_sections = PipelineService._normalize_content_structure(
            processed_sections
        )

        print("Step 5 : Generated summary/introduction/description ✔")

        gem_title = PipelineService._generate_title(
            processed_sections["content"]["summary"], journal
        )
        if gem_title[-1] == ".":
            gem_title = gem_title[:-1]

        print("Step 6 : Generated title ✔")

        # ---------- Step 6: Build final output ----------
        final_output = PipelineService._build_final_output(
            journal, gem_title, content_data, processed_sections["content"]
        )
        output_data = IOService.fetchOutputData()
        pulsus_output_instance = PulsusOutputStr(**final_output[journal.id])
        output_data[journal.id] = pulsus_output_instance.model_dump()
        IOService.saveOutputData(output_data)
        print("Step 7 : Saved output data ✔")

        # ---------- Step 7: Generate files ----------
        PipelineService._generate_html_and_pdf(journal, output_data)
        print("Step 11 : Generated HTML and PDF ✔")

        # ---------- Step 8: Write input to DB (only after PDF success) ----------
        IOService.saveInputData(data)
        print("Step 12 : Saved journal input to DB ✔")

        # ---------- Step 8: Return success ----------
        return JSONResponse(
            status_code=200,
            content={
                "Status": f"Data added and files generated successfully in PDFStorePulsus/{journal.id}/ ✔."
            },
        )

    # ------------------------------------------------------------------
    # Synchronous twin — designed for concurrent ThreadPoolExecutor use.
    # Returns a plain dict so the caller (excel_routes) can build SSE
    # events without caring about HTTP response objects.
    # All shared-file read-modify-write operations are performed while
    # holding IOService._db_lock so concurrent workers cannot corrupt
    # each other's DB entries.
    # ------------------------------------------------------------------
    @staticmethod
    def process_journal_sync(journal: PulsusInputStr) -> dict:
        """
        Blocking (synchronous) version of process_journal().
        Safe to run inside a ThreadPoolExecutor.

        Returns:
            {"status": "success", "id": journal_id}           on success
            {"status": "error",   "id": journal_id, "error": str}  on failure
        """
        from Apps.services.io_service import _db_lock  # module-level threading.Lock

        journal_id = journal.id.strip()
        step_start = _time.time()          # wall-clock start of the whole job
        t_step     = _time.time()          # reused per step for delta timing

        _dbg(journal_id, "━━━ JOB START ━━━")
        try:
            # ---------- Step 1: Validate + stage input (do NOT write to DB yet) ----------
            IOService.INPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

            _dbg(journal_id, "Step 1 | Waiting for _db_lock (input validate)…")
            t_step = _time.time()
            with _db_lock:
                _dbg(journal_id, "Step 1 | _db_lock acquired", t_step)
                data = IOService.fetchInputData()
                journal.id = journal_id
                journal.author = journal.author.strip()
                if journal.id in data:
                    raise ValueError(f"Journal ID '{journal.id}' already exists in the database.")
                data[journal.id] = journal.model_dump(exclude=["id"])
                # Stage entry in memory; DB write is deferred until PDF is generated successfully
            _dbg(journal_id, "Step 1 | _db_lock released — input staged ✔", t_step)

            # ---------- Step 2: Build LLM Prompt ----------
            t_step = _time.time()
            _dbg(journal_id, "Step 2 | Building LLM prompt…")
            prompt = PipelineService._build_prompt(journal)
            _dbg(journal_id, "Step 2 | Prompt ready ✔", t_step)

            # ---------- Step 3,4: Generate + Parse Gemini JSON ----------
            t_step = _time.time()
            _dbg(journal_id, "Step 3-4 | Sending references prompt to Gemini (may block)…")
            content_data = PipelineService._parse_gemini_response(prompt)
            _dbg(journal_id, "Step 3-4 | Gemini response parsed ✔", t_step)

            # ---------- Step 5: Create title, abstract, summary ----------
            t_step = _time.time()
            _dbg(journal_id, "Step 5 | Sending sections prompt to Gemini (may block)…")
            processed_sections = PipelineService._process_sections(content_data, journal)
            processed_sections = PipelineService._normalize_content_structure(processed_sections)
            _dbg(journal_id, "Step 5 | Sections generated ✔", t_step)

            t_step = _time.time()
            _dbg(journal_id, "Step 6a | Sending title prompt to Gemini (may block)…")
            gem_title = PipelineService._generate_title(
                processed_sections["content"]["summary"], journal
            )
            if gem_title and gem_title[-1] == ".":
                gem_title = gem_title[:-1]
            _dbg(journal_id, "Step 6a | Title generated ✔", t_step)

            # ---------- Step 6b: Build final output + save output DB ----------
            t_step = _time.time()
            _dbg(journal_id, "Step 6b | Building final output dict…")
            final_output = PipelineService._build_final_output(
                journal, gem_title, content_data, processed_sections["content"]
            )
            _dbg(journal_id, "Step 6b | Final output dict built ✔", t_step)

            _dbg(journal_id, "Step 7 | Waiting for _db_lock (save output DB)…")
            t_step = _time.time()
            with _db_lock:
                _dbg(journal_id, "Step 7 | _db_lock acquired", t_step)
                output_data = IOService.fetchOutputData()
                pulsus_output_instance = PulsusOutputStr(**final_output[journal.id])
                output_data[journal.id] = pulsus_output_instance.model_dump()
                IOService.saveOutputData(output_data)
            _dbg(journal_id, "Step 7 | _db_lock released — output DB saved ✔", t_step)

            # ---------- Step 7b: Generate HTML + PDF (CPU-bound, no shared state) ----------
            # Snapshot output_data under lock to avoid race with concurrent writers
            _dbg(journal_id, "Step 7b | Waiting for _db_lock (snapshot output for HTML/PDF gen)…")
            t_step = _time.time()
            with _db_lock:
                _dbg(journal_id, "Step 7b | _db_lock acquired", t_step)
                output_data_for_gen = IOService.fetchOutputData()
            _dbg(journal_id, "Step 7b | _db_lock released — output snapshot taken ✔", t_step)

            t_step = _time.time()
            _dbg(journal_id, "Step 8-11 | Starting HTML + PDF generation (xelatex, may take 30-120 s)…")
            PipelineService._generate_html_and_pdf(journal, output_data_for_gen)
            _dbg(journal_id, "Step 8-11 | HTML and PDF generated ✔", t_step)

            # ---------- Step 12: Write input to DB (only after PDF success) ----------
            _dbg(journal_id, "Step 12 | Waiting for _db_lock (save input DB)…")
            t_step = _time.time()
            with _db_lock:
                _dbg(journal_id, "Step 12 | _db_lock acquired", t_step)
                IOService.saveInputData(data)
            _dbg(journal_id, "Step 12 | _db_lock released — input DB saved ✔", t_step)

            _dbg(journal_id, f"━━━ JOB COMPLETE ✔  (total {_time.time() - step_start:.1f}s) ━━━")
            return {"status": "success", "id": journal_id}

        except Exception as exc:
            _dbg(journal_id, f"━━━ JOB FAILED after {_time.time() - step_start:.1f}s | ERROR: {exc} ━━━")
            # Rollback: remove orphaned output DB entry if it was written before failure
            try:
                _dbg(journal_id, "Rollback | Waiting for _db_lock…")
                t_rb = _time.time()
                with _db_lock:
                    _dbg(journal_id, "Rollback | _db_lock acquired", t_rb)
                    output_data_rollback = IOService.fetchOutputData()
                    if journal_id in output_data_rollback:
                        del output_data_rollback[journal_id]
                        IOService.saveOutputData(output_data_rollback)
                        _dbg(journal_id, "Rollback | orphaned output DB entry removed ✔")
                _dbg(journal_id, "Rollback | _db_lock released", t_rb)
            except Exception as rb_exc:
                _dbg(journal_id, f"Rollback | FAILED: {rb_exc}")
            return {"status": "error", "id": journal_id, "error": str(exc)}

    # =====================================================================================================================================
    # Internal helper methods
    # =====================================================================================================================================

    @staticmethod
    def _build_prompt(journal: PulsusInputStr) -> str:
        """Delegate Step-1 prompt construction to the journal's template."""
        return TemplateFactory.get(journal.brandName).get_references_prompt(journal)


    @staticmethod
    def _ask_gemini_with_retries(prompt: str, retries: int = 10) -> str:
        thr = threading.current_thread().name
        for attempt in range(retries):
            t_gem = _time.time()
            print(f"[{_time.strftime('%H:%M:%S')}] [{thr}] Gemini call attempt {attempt + 1}/{retries} → sending {len(prompt)} chars…")
            try:
                response = PipelineService.gemClient.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=prompt
                    # config={
                    #     "tools": [
                    #         {
                    #             "google_search": {}
                    #         }
                    #     ]
                    # }
                )
                elapsed = _time.time() - t_gem
                print(f"[{_time.strftime('%H:%M:%S')}] [{thr}] Gemini response received in {elapsed:.2f}s ({len(response.text)} chars)")
                return response.text
            except Exception as e:
                elapsed = _time.time() - t_gem
                print(f"[{_time.strftime('%H:%M:%S')}] [{thr}] Gemini attempt {attempt + 1} FAILED after {elapsed:.2f}s: {e}")
                time.sleep(3)
                if attempt == retries - 1:
                    raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def _parse_gemini_response(prompt: str, retries: int = 10) -> dict:
        """
        Generate Gemini response and parse JSON.
        If parsing fails, retry up to `retries` times by regenerating Gemini output.
        """
        attempt = 0
        while attempt < retries:
            gem_response = PipelineService._ask_gemini_with_retries(prompt)

            try:
                raw_json = IOService.extract_json_from_markdown(gem_response)
                return json.loads(raw_json)

            except json.JSONDecodeError as e:
                attempt += 1
                print(f"JSON parsing failed (attempt {attempt}/{retries}): {e}")
                if attempt >= retries:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to parse Gemini JSON after {retries} attempts: {e}",
                    )
                print("Retrying Gemini generation...")
                time.sleep(2)

    @staticmethod
    def _normalize_content_structure(parsed_json: dict) -> dict:
        """
        Normalize Gemini response structure.
        Ensures the output always follows:
        {"content": {...}} format.
        """
        if "content" in parsed_json:
            return parsed_json  # already correct format

        # If flat, wrap it inside 'content'
        return {"content": parsed_json}

    @staticmethod
    def _process_sections(content_data: dict, journal: PulsusInputStr) -> dict:
        """Delegate Step-2 prompt to the journal's template, then parse + normalise."""
        prompt = TemplateFactory.get(journal.brandName).get_sections_prompt(content_data)
        parsed = PipelineService._parse_gemini_response(prompt)
        normalized = PipelineService._normalize_content_structure(parsed)
        return normalized

    @staticmethod
    def _generate_title(summary: str, journal: PulsusInputStr) -> str:
        """Delegate Step-3 title prompt to the template, then apply format_title."""
        template = TemplateFactory.get(journal.brandName)
        prompt = template.get_title_prompt(summary)
        response = PipelineService._ask_gemini_with_retries(prompt)
        return template.format_title(response)

    # =======================
    # AUTHOR FORMAT UTILITIES
    # =======================

    @staticmethod
    def _format_author_name(full_name: str) -> str:
        """
        'Swarupa N. Kulkarni' → 'Swarupa NK'
        """
        parts = full_name.replace(".", "").split()
        if len(parts) == 1:
            return parts[0]

        first = parts[0]
        initials = "".join(p[0] for p in parts[1:])
        return f"{first} {initials}"

    @staticmethod
    def _format_authors_list(author_list: list[str]) -> str:
        formatted = [
            PipelineService._format_author_name(a)
            for a in author_list
            if isinstance(a, str)
        ]
        return ", ".join(formatted) + "."

    @staticmethod
    def _build_final_output(journal, gem_title, content_data, gem_info):
        """
        Stores:
          - authors_full  (full names)
          - authors_short (initials format)
          - RAW reference fields (title, year, journal, etc.)

        Reference string is NOT generated here.
        Each LaTeX brand template will format its own version.
        """

        processed_content = {}

        # ----------------------------------------------------
        #  Process content items (C001, C002, ...)
        # ----------------------------------------------------
        # Process each reference C001, C002...

        for key, item in content_data.get("content", {}).items():

            full_authors_list = item.get("authors", [])
            authors_full = ", ".join(full_authors_list) + "."
            authors_short = PipelineService._format_authors_list(full_authors_list)

            processed_content[key] = {
                "title": item.get("title", ""),
                "journalShortName": item.get("journalShortName", ""),
                "authors_full": authors_full,
                "authors_short": authors_short,
                "published": item.get("published", ""),
                "pageRangeOrNumber": item.get("pageRangeOrNumber", ""),
                "volume": item.get("volume", ""),
                "issues": item.get("issues", ""),
                "DOI": item.get("DOI", ""),
                "url": item.get("url", ""),
                "parentLink": item.get("parentLink", ""),
                "subContent": item.get("subContent", ""),
            }

        output = {
            journal.id: {
                "title": gem_title,
                "journalName": journal.journalName,
                "shortJournalName": journal.shortJournalName,
                "secondShortName": journal.secondShortName,
                "type": journal.type,
                "author": journal.author,
                "email": journal.email,
                "brandName": journal.brandName,
                "authorsDepartment": journal.authorsDepartment,
                "journalYearVolumeIssue": f"{journal.shortJournalName}, Volume {journal.volume}:{journal.issues}, {journal.published.split('-')[-1]}",
                "introduction": gem_info["introduction"],
                "description": gem_info["description"],
                "abstract": gem_info["abstract"],
                "discussion": gem_info["discussion"],
                "keywords": gem_info["keywords"],
                # 🔥 Use processed content here
                "content": processed_content,
                "doi": journal.doi,
                "received": journal.received,
                "editorAssigned": journal.editorAssigned,
                "reviewed": journal.reviewed,
                "revised": journal.revised,
                "published": journal.published,
                "year": int(journal.published.split("-")[-1]),
                "month": str(journal.published.split("-")[1]),
                "manuscriptNo": journal.manuscriptNo,
                **TemplateFactory.get(journal.brandName).format_manuscript_numbers(journal.manuscriptNo),
                **dict(zip(
                    ("volume", "issues"),
                    TemplateFactory.get(journal.brandName).format_volume_issue(
                        journal.volume, journal.issues
                    ),
                )),
                "pdfNo": journal.pdfNo,
                "ISSN": journal.ISSN,
                "imgPath": journal.imgPath,
                "parentLink": str(journal.parentLink),
                "conclusion": gem_info["summary"],
                "issueType": journal.issueType if journal.issueType else "Issue",
            }
        }
        return output

    @staticmethod
    def _generate_html_and_pdf(journal, output_data):
        """Move all your LaTeX + HTML rendering logic here."""
        # --- Centralized Directory Setup ---
        
        # Create a single directory for all of this journal's pdf, .html, .tex files.
        output_base_dir = pathOfPathLib("Apps/DB/PDFStorePulsus")
        journal_folder = output_base_dir / journal.id
        journal_folder.mkdir(parents=True, exist_ok=True)

        # Create a working directory for output and log files
        output_log_dir = pathOfPathLib("Apps/DB/TempLogsPulsus")
        log_folder = output_log_dir / journal.id
        log_folder.mkdir(parents=True, exist_ok=True)

        print("Step 8.1 : Final response ✔")

        # --- 9: Create HTML file ---
        env_html = Environment(
            loader=FileSystemLoader(pathOfPathLib("Apps/templates/"))
        )
        try:
            html_template = env_html.get_template("Format.html")
            forHtml = copy.deepcopy(output_data[journal.id])

            # Logic for processing in-text citations for HTML (numeric or author-date)
            forHtml = TemplateFactory.get(journal.brandName).link_in_text_citations_html(forHtml)

            forHtml["description"] = forHtml["description"].replace(r"\n\n", "</p><p>")
            forHtml["description"] = forHtml["description"].replace(r"\n", "</p><p>")

            forHtml["storeBody"] = TemplateFactory.get(journal.brandName).get_html_body_sections(forHtml)

            count = 0
            forHtml["storeRefPart"] = ""
            for i in forHtml["content"].values():
                count += 1
                i["issues"] = f"({i['issues']})" if i.get("issues") else ""
                temp = TemplateFactory.get(journal.brandName).render_html_reference(count, i)

                forHtml["storeRefPart"] = f"""{forHtml['storeRefPart']}\n{temp}"""

            department_parts = forHtml["authorsDepartment"].split(",")
            if len(department_parts) > 1:
                forHtml["prefixAuthorDepartment"] = f"{department_parts[0]}<br />"
                forHtml["suffixAuthorDepartment"] = (
                    f"{','.join(department_parts[1:])}.<br />"
                )
            else:
                forHtml["prefixAuthorDepartment"] = forHtml["authorsDepartment"]
                forHtml["suffixAuthorDepartment"] = "<br />"

            rendered_html = html_template.render(**forHtml)

            # Save the HTML file inside the journal's dedicated folder
            html_file_path = journal_folder / f"{journal.id}.html"
            html_file_path.write_text(rendered_html, encoding="utf-8")

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to generate HTML file: {str(e)}"
            )

        print("Step 9 : Created HTML file ✔")

        # --- 10: Create PDF file ---
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
            loader=FileSystemLoader(pathOfPathLib("Apps/templates")),
        )

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

        env_latex.filters["latex_escape"] = latex_escape
        latex_template = env_latex.get_template(journal.brandName)

        template = TemplateFactory.get(journal.brandName)
        lang_map = LatexLanguageConfig().get_lang_map(template.latex_font)

        # --- ensure initial PDF has an English preamble and mark language in saved record ---
        default_cfg = lang_map.get("default")

        # Build preamble: polyglossia + the font block stored in default_cfg
        preamble = (
            "\\usepackage{polyglossia}\n"
            + default_cfg["polyglossia"]
            + "\n"
            + default_cfg["font"]
        )
        output_data[journal.id]["preamble"] = preamble
        output_data[journal.id]["lang_name"] = "english"

        # record original language so later translation flow can detect existing language if needed
        output_data[journal.id]["lang"] = "en"

        forPdf = copy.deepcopy(output_data[journal.id])

        # Logic for processing in-text citations for PDF/LaTeX (brand-specific)
        forPdf = TemplateFactory.get(journal.brandName).link_in_text_citations_pdf(forPdf)

        rendered_latex = latex_template.render(**forPdf)

        # Save the .tex file inside the journal's dedicated folder
        tex_file_path = journal_folder / f"{journal.id}.tex"
        tex_file_path.write_text(rendered_latex, encoding="utf-8")

        # Compile LaTeX to PDF. Run from within the journal's folder.
        _XELATEX_TIMEOUT = 120  # seconds per xelatex pass — increase if needed
        thr = threading.current_thread().name
        for i in range(2):
            t_latex = _time.time()
            print(f"[{_time.strftime('%H:%M:%S')}] [{thr}] [{journal.id}] xelatex pass {i + 1}/2 → starting (timeout={_XELATEX_TIMEOUT}s)…")
            try:
                result = subprocess.run(
                    [
                        "xelatex",
                        "-interaction=nonstopmode",
                        tex_file_path.name,
                    ],
                    capture_output=True,  # Capture stdout/stderr
                    text=True,
                    cwd=journal_folder,  # CRITICAL: Set the working directory
                    timeout=_XELATEX_TIMEOUT,
                )
            except subprocess.TimeoutExpired:
                elapsed = _time.time() - t_latex
                raise HTTPException(
                    status_code=500,
                    detail=f"xelatex pass {i + 1} timed out after {elapsed:.0f}s — possible infinite loop in LaTeX source.",
                )
            elapsed = _time.time() - t_latex
            print(f"[{_time.strftime('%H:%M:%S')}] [{thr}] [{journal.id}] xelatex pass {i + 1}/2 → finished in {elapsed:.2f}s (returncode={result.returncode})")

            if result.returncode != 0:
                log_file_path = log_folder / f"{journal.id}.log"
                log_file_path = log_file_path.with_suffix(".log")

                # The log file is already saved by xelatex, so we just read it for the error message
                error_text = "Unknown LaTeX error. Check the log file."
                if log_file_path.exists():
                    with open(log_file_path, "r") as f:
                        lines = f.readlines()
                    error_snippets = [line for line in lines if line.startswith("! ")]
                    error_text = (
                        "\n".join(error_snippets)
                        or f"LaTeX compilation failed. Full log in {log_file_path}"
                    )

                raise HTTPException(
                    status_code=500,
                    detail=f"LaTeX compilation failed on run {i + 1}:\n\n{error_text}",
                )

        # --- Optional 3rd pass: inject real page range into pdfNo (brand opt-in only) ---
        if template.needs_page_count_recompile:
            pdf_file_path = journal_folder / f"{journal.id}.pdf"
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(pdf_file_path))
                total_pages = len(reader.pages)
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to read page count from first-pass PDF: {e}",
                )

            # Ask the brand template to format the final pdfNo string (e.g. "1-6")
            forPdf["pdfNo"] = template.build_pdf_no(total_pages)
            print(f"Step 10a: Page count = {total_pages}, pdfNo → '{forPdf['pdfNo']}' ✔")

            # Re-render the .tex file with the real pdfNo and recompile
            rendered_latex_final = latex_template.render(**forPdf)
            tex_file_path.write_text(rendered_latex_final, encoding="utf-8")

            t_latex3 = _time.time()
            print(f"[{_time.strftime('%H:%M:%S')}] [{thr}] [{journal.id}] xelatex pass 3/3 (page-count recompile) → starting (timeout={_XELATEX_TIMEOUT}s)…")
            try:
                result_final = subprocess.run(
                    [
                        "xelatex",
                        "-interaction=nonstopmode",
                        tex_file_path.name,
                    ],
                    capture_output=True,
                    text=True,
                    cwd=journal_folder,
                    timeout=_XELATEX_TIMEOUT,
                )
            except subprocess.TimeoutExpired:
                elapsed3 = _time.time() - t_latex3
                raise HTTPException(
                    status_code=500,
                    detail=f"xelatex pass 3 timed out after {elapsed3:.0f}s.",
                )
            elapsed3 = _time.time() - t_latex3
            print(f"[{_time.strftime('%H:%M:%S')}] [{thr}] [{journal.id}] xelatex pass 3/3 → finished in {elapsed3:.2f}s (returncode={result_final.returncode})")

            if result_final.returncode != 0:
                log_file_path = log_folder / f"{journal.id}.log"
                error_text = "Unknown LaTeX error in final recompile. Check the log file."
                if log_file_path.exists():
                    with open(log_file_path, "r") as f:
                        lines = f.readlines()
                    error_snippets = [line for line in lines if line.startswith("! ")]
                    error_text = (
                        "\n".join(error_snippets)
                        or f"LaTeX final recompile failed. Full log in {log_file_path}"
                    )
                raise HTTPException(
                    status_code=500,
                    detail=f"LaTeX final recompile (pass 3) failed:\n\n{error_text}",
                )

            print(f"[{_time.strftime('%H:%M:%S')}] [{thr}] [{journal.id}] Step 10b: Final PDF recompiled with real pdfNo ✔")

        for ext in [".log", ".aux", ".out"]:
            src = journal_folder / f"{journal.id}{ext}"
            dst = log_folder / f"{journal.id}{ext}"
            if src.exists():
                src.replace(dst)  # move file

        print("Step 10 : Create PDF file ✔")

        return JSONResponse(
            status_code=200,
            content={
                "Status": f"Data added and files generated successfully in PDFStorePulsus/{journal.id}/ ✔."
            },
        )
