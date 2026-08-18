"""
excel_routes.py
Handles Excel batch upload for bulk PDF generation.

Endpoints:
    POST /excel/validate       — Parse & validate the uploaded .xlsx file
    POST /excel/start-batch    — Run the full pipeline for each validated row (SSE stream)
"""

import io
import re
import asyncio
import datetime
import shutil
from pathlib import Path

import openpyxl
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from Apps.services.io_service import IOService
from Apps.services.pipeline_service import PipelineService
from Apps.models_journal import PulsusInputStr

router = APIRouter(prefix="/excel", tags=["Excel Batch Upload"])

# ---------------------------------------------------------------------------
# Expected column headers (order-independent, case-sensitive)
# ---------------------------------------------------------------------------
REQUIRED_COLUMNS = [
    "Date", "JournalID", "Type", "ManuscriptNo", "Brand",
    "JournalName", "ShortName", "Link", "ISSN", "VolumeNo",
    "IssueNo", "DOI", "PDFNo", "Keyword", "AuthorName",
    "Mail ID", "Affiliation",
]
OPTIONAL_COLUMNS = ["ImgPath"]
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

# Valid brand template filenames (loaded lazily inside the validator)
import os
_TEMPLATE_DIR = os.path.join("Apps", "templates")
_LOGO_DIR = os.path.join("Apps", "Logo")


def _get_valid_brands() -> set:
    try:
        return {f for f in os.listdir(_TEMPLATE_DIR) if f.endswith(".tex")}
    except Exception:
        return set()


def _get_valid_images() -> set:
    allowed = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".svg"}
    try:
        return {f for f in os.listdir(_LOGO_DIR) if os.path.splitext(f)[1].lower() in allowed}
    except Exception:
        return set()


# ---------------------------------------------------------------------------
# Row-level validator
# ---------------------------------------------------------------------------

def _validate_row(
    row_index: int,
    row: dict,
    existing_db_ids: set,
    seen_ids_in_file: set,
    valid_brands: set,
    valid_images: set,
) -> dict:
    """
    Validates a single row from the Excel sheet.
    Returns a dict:
        {
            "rowIndex": int,          # 1-based
            "data": dict,             # cleaned values
            "errors": dict,           # field -> error message (empty if valid)
            "valid": bool
        }
    """
    errors: dict = {}

    def get(col: str) -> str:
        return str(row.get(col, "") or "").strip()

    # --- JournalID ---
    journal_id = get("JournalID")
    if not journal_id:
        errors["JournalID"] = "JournalID is required."
    elif len(journal_id) < 3:
        errors["JournalID"] = f"JournalID '{journal_id}' is too short (min 3 characters)."
    elif len(journal_id) > 6:
        errors["JournalID"] = f"JournalID '{journal_id}' exceeds 6 characters."
    elif journal_id in existing_db_ids:
        errors["JournalID"] = f"JournalID '{journal_id}' already exists in the database."
    elif journal_id in seen_ids_in_file:
        errors["JournalID"] = f"JournalID '{journal_id}' is duplicated within this Excel file."
    else:
        seen_ids_in_file.add(journal_id)

    # --- Date (received) ---
    # openpyxl may return a datetime/date object directly for date-formatted cells
    # (e.g. when a user types 1/1/2026 in Excel).  Handle that before stringifying.
    raw_date_cell = row.get("Date", "")
    if isinstance(raw_date_cell, (datetime.datetime, datetime.date)):
        # Already a proper date object — no parsing needed
        parsed_date = raw_date_cell.date() if isinstance(raw_date_cell, datetime.datetime) else raw_date_cell
        date_val = parsed_date.strftime("%Y-%m-%d")
    else:
        date_val = str(raw_date_cell or "").strip()
        parsed_date = None

    if not date_val:
        errors["Date"] = "Date is required."
    elif parsed_date is None:
        # Try a range of common string formats, including single-digit day/month variants
        for fmt in (
            "%Y-%m-%d",        # 2026-01-01
            "%d-%m-%Y",        # 01-01-2026
            "%d/%m/%Y",        # 01/01/2026
            "%m/%d/%Y",        # 01/01/2026 (US)
            "%d-%b-%Y",        # 01-Jan-2026
            "%Y/%m/%d",        # 2026/01/01
            "%Y-%m-%d %H:%M:%S",   # 2026-01-01 00:00:00  (datetime string)
        ):
            try:
                parsed_date = datetime.datetime.strptime(date_val, fmt).date()
                date_val = parsed_date.strftime("%Y-%m-%d")   # normalise to YYYY-MM-DD
                break
            except ValueError:
                continue
        if parsed_date is None:
            errors["Date"] = (
                f"'{date_val}' is not a recognisable date "
                "(use YYYY-MM-DD, DD-MM-YYYY, or D/M/YYYY)."
            )

    # --- AuthorName ---
    author = get("AuthorName")
    if not author:
        errors["AuthorName"] = "AuthorName is required."
    elif len(author.split()) < 2:
        errors["AuthorName"] = "AuthorName must contain at least a first name and a last name."

    # --- Mail ID ---
    email = get("Mail ID")
    email_pattern = r"^[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9.\-]+$"
    if not email:
        errors["Mail ID"] = "Mail ID (email) is required."
    elif not re.match(email_pattern, email):
        errors["Mail ID"] = f"'{email}' is not a valid email address."

    # --- Brand ---
    brand = get("Brand")
    if not brand:
        errors["Brand"] = "Brand is required."
    elif brand not in valid_brands:
        errors["Brand"] = (
            f"Brand '{brand}' is not a valid template. Available: {', '.join(sorted(valid_brands))}"
        )

    # --- Link (parentLink) ---
    link = get("Link")
    url_pattern = r"^https?://.+"
    if not link:
        errors["Link"] = "Link (parent URL) is required."
    elif not re.match(url_pattern, link):
        errors["Link"] = f"'{link}' is not a valid URL (must start with http:// or https://)."

    # --- VolumeNo ---
    volume_str = get("VolumeNo")
    if not volume_str:
        errors["VolumeNo"] = "VolumeNo is required."
    else:
        try:
            vol = int(float(volume_str))
            if vol <= 0:
                raise ValueError
            volume_str = str(vol)
        except ValueError:
            errors["VolumeNo"] = f"'{volume_str}' must be a positive integer."

    # --- IssueNo ---
    issue_str = get("IssueNo")
    if not issue_str:
        errors["IssueNo"] = "IssueNo is required."
    else:
        try:
            iss = int(float(issue_str))
            if iss <= 0:
                raise ValueError
            issue_str = str(iss)
        except ValueError:
            errors["IssueNo"] = f"'{issue_str}' must be a positive integer."

    # --- PDFNo ---
    pdf_str = get("PDFNo")
    if not pdf_str:
        errors["PDFNo"] = "PDFNo is required."
    else:
        try:
            pdf = int(float(pdf_str))
            if pdf <= 0:
                raise ValueError
            pdf_str = str(pdf)
        except ValueError:
            errors["PDFNo"] = f"'{pdf_str}' must be a positive integer."

    # --- Required text fields ---
    for field, col in [
        ("Type", "Type"),
        ("ManuscriptNo", "ManuscriptNo"),
        ("JournalName", "JournalName"),
        ("ShortName", "ShortName"),
        ("Keyword", "Keyword"),
        ("Affiliation", "Affiliation"),
    ]:
        if not get(col):
            errors[col] = f"{col} is required."

    # --- ImgPath (optional) ---
    img_path = get("ImgPath")
    if img_path and img_path not in valid_images:
        errors["ImgPath"] = (
            f"Image '{img_path}' not found in Logo directory. "
            f"Leave blank if not applicable."
        )

    # --- ISSN / DOI (optional, no format enforcement) ---

    cleaned = {
        "id": journal_id,
        "received": date_val,
        "type": get("Type"),
        "manuscriptNo": get("ManuscriptNo"),
        "brandName": brand,
        "journalName": get("JournalName"),
        "shortJournalName": get("ShortName"),
        "parentLink": link,
        "ISSN": get("ISSN") or None,
        "volume": volume_str,
        "issues": issue_str,
        "doi": get("DOI") or "",
        "pdfNo": pdf_str,
        "topic": get("Keyword"),
        "author": author,
        "email": email,
        "authorsDepartment": get("Affiliation"),
        "imgPath": img_path or None,
    }

    return {
        "rowIndex": row_index,
        "data": cleaned,
        "errors": errors,
        "valid": len(errors) == 0,
    }


# ---------------------------------------------------------------------------
# GET /excel/options  — return available brands & images for dropdowns
# ---------------------------------------------------------------------------

@router.get("/options")
async def get_excel_options():
    """Return sorted lists of valid brand templates and logo images."""
    return JSONResponse(content={
        "brands": sorted(_get_valid_brands()),
        "images": sorted(_get_valid_images()),
    })


# ---------------------------------------------------------------------------
# POST /excel/validate
# ---------------------------------------------------------------------------

@router.post("/validate")
async def validate_excel(file: UploadFile = File(...)):
    """
    Accepts an .xlsx file upload.
    Parses headers, checks column names, then validates every row.
    Returns JSON with per-row results.
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx or .xls files are accepted.")

    content = await file.read()
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not open the Excel file: {e}")

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    if not rows:
        raise HTTPException(status_code=400, detail="The Excel file is empty.")

    # --- Header check ---
    header_row = [str(c).strip() if c is not None else "" for c in rows[0]]
    missing_required = [c for c in REQUIRED_COLUMNS if c not in header_row]
    unknown_cols = [c for c in header_row if c and c not in ALL_COLUMNS]

    if missing_required:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Missing required column headers.",
                "missingColumns": missing_required,
            },
        )

    # Build row dicts
    data_rows = []
    for r in rows[1:]:
        if all((c is None or str(c).strip() == "") for c in r):
            continue  # skip blank rows
        data_rows.append(dict(zip(header_row, r)))

    if not data_rows:
        raise HTTPException(status_code=400, detail="The Excel file has headers but no data rows.")

    # Validate each row
    existing_db_ids = set(IOService.fetchInputData().keys())
    seen_ids_in_file: set = set()
    valid_brands = _get_valid_brands()
    valid_images = _get_valid_images()

    results = []
    for idx, row in enumerate(data_rows, start=1):
        result = _validate_row(idx, row, existing_db_ids, seen_ids_in_file, valid_brands, valid_images)
        results.append(result)

    total = len(results)
    valid_count = sum(1 for r in results if r["valid"])
    error_count = total - valid_count

    return JSONResponse(
        status_code=200,
        content={
            "totalRows": total,
            "validRows": valid_count,
            "errorRows": error_count,
            "unknownColumns": unknown_cols,
            "rows": results,
        },
    )


# ---------------------------------------------------------------------------
# POST /excel/revalidate  — re-check already-parsed rows after inline edits
# ---------------------------------------------------------------------------

@router.post("/revalidate")
async def revalidate_rows(payload: dict):
    """
    Accepts a JSON body: { "rows": [ { "rowIndex": int, "data": {...}, ... } ] }
    Re-runs validation on each row's data dict (already parsed, just re-check rules).
    Returns the same shape as /validate.
    """
    rows = payload.get("rows", [])
    if not rows:
        raise HTTPException(status_code=400, detail="No rows provided.")

    # Build a reverse-map from data keys → column names so we can call _validate_row
    def data_to_excel_row(data: dict) -> dict:
        return {
            "JournalID":    data.get("id", ""),
            "Date":         data.get("received", ""),
            "Type":         data.get("type", ""),
            "ManuscriptNo": data.get("manuscriptNo", ""),
            "Brand":        data.get("brandName", ""),
            "JournalName":  data.get("journalName", ""),
            "ShortName":    data.get("shortJournalName", ""),
            "Link":         data.get("parentLink", ""),
            "ISSN":         data.get("ISSN", ""),
            "VolumeNo":     data.get("volume", ""),
            "IssueNo":      data.get("issues", ""),
            "DOI":          data.get("doi", ""),
            "PDFNo":        data.get("pdfNo", ""),
            "Keyword":      data.get("topic", ""),
            "AuthorName":   data.get("author", ""),
            "Mail ID":      data.get("email", ""),
            "Affiliation":  data.get("authorsDepartment", ""),
            "ImgPath":      data.get("imgPath", ""),
        }

    existing_db_ids = set(IOService.fetchInputData().keys())
    seen_ids_in_file: set = set()
    valid_brands = _get_valid_brands()
    valid_images = _get_valid_images()

    results = []
    for row_payload in rows:
        row_index = row_payload.get("rowIndex", 0)
        excel_row = data_to_excel_row(row_payload.get("data", {}))
        result = _validate_row(
            row_index, excel_row,
            existing_db_ids, seen_ids_in_file,
            valid_brands, valid_images,
        )
        results.append(result)

    total = len(results)
    valid_count = sum(1 for r in results if r["valid"])
    error_count = total - valid_count

    return JSONResponse(
        status_code=200,
        content={
            "totalRows": total,
            "validRows": valid_count,
            "errorRows": error_count,
            "unknownColumns": [],
            "rows": results,
        },
    )



# ---------------------------------------------------------------------------
# POST /excel/start-batch  (SSE streaming, parallel execution)
# ---------------------------------------------------------------------------

@router.post("/start-batch")
async def start_batch(payload: dict):
    """
    Accepts JSON body:
        {
            "rows":        [ { ...cleaned row data... }, ... ],
            "max_workers": 4          # optional, 1-10, default 4
        }

    Runs the full pipeline for EVERY row in parallel using a ThreadPoolExecutor.
    Streams progress as Server-Sent Events (SSE).
    Events may arrive out of order — each event carries 'id' and 'row' so the
    frontend can track individual journals regardless of arrival order.

    Also copies each generated PDF into a unique numbered bulk session folder
    under Apps/DB/BulkPDF/ (e.g. Bulk_001/) named {journal_id}.pdf.
    """
    import asyncio
    import json as _json
    from concurrent.futures import ThreadPoolExecutor

    rows = payload.get("rows", [])
    if not rows:
        raise HTTPException(status_code=400, detail="No rows provided.")

    # Clamp max_workers between 1 and 10
    max_workers = max(1, min(int(payload.get("max_workers", 4)), 10))

    # --- Create a unique numbered bulk session folder ---
    bulk_base = Path("Apps/DB/BulkPDF")
    bulk_base.mkdir(parents=True, exist_ok=True)

    existing_nums = []
    for item in bulk_base.iterdir():
        if item.is_dir() and item.name.startswith("Bulk_"):
            try:
                existing_nums.append(int(item.name.split("_", 1)[1]))
            except ValueError:
                pass
    next_num = max(existing_nums, default=0) + 1
    bulk_session_folder = bulk_base / f"Bulk_{next_num:03d}"
    bulk_session_folder.mkdir(parents=True, exist_ok=True)

    pdf_store = Path("Apps/DB/PDFStorePulsus")

    async def event_stream():
        total = len(rows)
        loop = asyncio.get_running_loop()   # safe in Python 3.10+

        # Build (row_index, PulsusInputStr) pairs upfront
        journals_indexed = []
        for idx, row_data in enumerate(rows, start=1):
            try:
                row_copy = dict(row_data)
                row_copy["volume"] = int(row_copy.get("volume", 1))
                row_copy["issues"]  = int(row_copy.get("issues",  1))
                row_copy["pdfNo"]   = int(row_copy.get("pdfNo",   1))
                journal = PulsusInputStr(**row_copy)
                journals_indexed.append((idx, journal))
            except Exception as build_err:
                journal_id = row_data.get("id", f"row-{idx}")
                yield f"data: {_json.dumps({'event': 'error', 'row': idx, 'total': total, 'id': journal_id, 'error': f'Failed to build journal object: {build_err}'})}\n\n"

        if not journals_indexed:
            yield f"data: {_json.dumps({'event': 'complete', 'total': total, 'bulkFolder': bulk_session_folder.name})}\n\n"
            return

        # Emit a "start" event for each journal before kicking off the pool
        for idx, journal in journals_indexed:
            yield f"data: {_json.dumps({'event': 'start', 'row': idx, 'total': total, 'id': journal.id})}\n\n"

        # Submit all jobs to the thread pool concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Map future → (row_index, journal_id) for result attribution
            future_map = {
                loop.run_in_executor(
                    executor,
                    PipelineService.process_journal_sync,
                    journal,
                ): (idx, journal.id)
                for idx, journal in journals_indexed
            }

            # Yield SSE events as each future completes (asyncio.as_completed equivalent)
            pending = set(future_map.keys())
            while pending:
                done, pending = await asyncio.wait(
                    pending, return_when=asyncio.FIRST_COMPLETED
                )
                for fut in done:
                    row_idx, journal_id = future_map[fut]
                    try:
                        result = fut.result()
                    except Exception as exc:
                        result = {"status": "error", "id": journal_id, "error": str(exc)}

                    if result.get("status") == "success":
                        # Copy the generated PDF into the bulk session folder,
                        # grouped by the alphabetic prefix of the journal ID.
                        # e.g. "cbm01" → subfolder "cbm", "jop03" → subfolder "jop"
                        src_pdf = pdf_store / journal_id / f"{journal_id}.pdf"
                        if src_pdf.exists():
                            journal_prefix = "".join(
                                ch for ch in journal_id if ch.isalpha()
                            )
                            journal_subfolder = bulk_session_folder / journal_prefix
                            journal_subfolder.mkdir(parents=True, exist_ok=True)
                            dst_pdf = journal_subfolder / f"{journal_id}.pdf"
                            shutil.copy2(str(src_pdf), str(dst_pdf))

                        # Also copy the HTML file with the same name
                        src_html = pdf_store / journal_id / f"{journal_id}.html"
                        if src_html.exists():
                            journal_prefix = "".join(
                                ch for ch in journal_id if ch.isalpha()
                            )
                            journal_subfolder = bulk_session_folder / journal_prefix
                            journal_subfolder.mkdir(parents=True, exist_ok=True)
                            dst_html = journal_subfolder / f"{journal_id}.html"
                            shutil.copy2(str(src_html), str(dst_html))

                        yield (
                            f"data: {_json.dumps({'event': 'done', 'row': row_idx, 'total': total, 'id': journal_id, 'status': 'success', 'bulkFolder': bulk_session_folder.name})}\n\n"
                        )
                    else:
                        yield (
                            f"data: {_json.dumps({'event': 'error', 'row': row_idx, 'total': total, 'id': journal_id, 'error': result.get('error', 'Unknown error')})}\n\n"
                        )

                    await asyncio.sleep(0)   # yield control so the event loop can flush SSE

        yield f"data: {_json.dumps({'event': 'complete', 'total': total, 'bulkFolder': bulk_session_folder.name})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

