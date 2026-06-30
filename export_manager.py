"""
export_manager.py — ReqFlow AI · Unified Export Controller
===========================================================
Coordinates and manages the export operations for all document formats
(PDF, DOCX, Excel, Markdown) and sections.
"""

from __future__ import annotations

from typing import Optional, Union
import docx_export
import pdf_export
import excel_export
import markdown_export

# ---------------------------------------------------------------------------
# Format Mapping Constants
# ---------------------------------------------------------------------------
MIME_TYPES = {
    "PDF": pdf_export.PDF_MIME,
    "DOCX": docx_export.DOCX_MIME,
    "EXCEL": excel_export.EXCEL_MIME,
    "MARKDOWN": markdown_export.MARKDOWN_MIME,
}

EXTENSIONS = {
    "PDF": "pdf",
    "DOCX": "docx",
    "EXCEL": "xlsx",
    "MARKDOWN": "md",
}

# Display names in dropdown to database section key mapping
DOC_TYPE_TO_KEY = {
    "BRD": "brd",
    "SRS": "srs",
    "Use Cases": "use_cases",
    "User Stories": "user_stories",
    "Database Design": "db_suggestions",
    "KPI": "kpis",
    "Workflow": "workflow",
    "Reports": "reports",
}

DOC_KEY_TO_LABEL = {
    "brd": "Business Requirements Document (BRD)",
    "srs": "Software Requirements Specification (SRS)",
    "use_cases": "Use Case Specifications",
    "user_stories": "User Stories & Acceptance Criteria",
    "db_suggestions": "Database Design Suggestions",
    "kpis": "Key Performance Indicators (KPI)",
    "workflow": "Workflow Specifications",
    "reports": "Report Specifications",
}

# ===========================================================================
#  Unified Export Dispatcher
# ===========================================================================
def get_export_data(
    project_name: str,
    industry: str,
    timestamp: str,
    doc_type: str,  # 'BRD', 'SRS', ..., 'Full Requirement Suite'
    format_type: str,  # 'PDF', 'DOCX', 'Excel', 'Markdown'
    project_data: dict[str, str]
) -> tuple[Union[bytes, str], str, str]:
    """
    Dispatches document configurations to the correct generation engine.

    Returns
    -------
    tuple: (data_payload, file_name, mime_type)
        data_payload: bytes or string matching format
        file_name: clean target download file name
        mime_type: correct MIME string
    """
    fmt = format_type.upper()
    if fmt == "EXCEL":
        fmt = "EXCEL" # standard
        
    mime = MIME_TYPES.get(fmt, "text/plain")
    ext = EXTENSIONS.get(fmt, "txt")
    
    clean_proj_name = project_name.replace(" ", "_")
    
    # ── CASE 1: Full Suite Export
    if doc_type == "Full Requirement Suite":
        file_name = f"{clean_proj_name}_Complete_Suite.{ext}"
        
        # Prepare all sections for builder functions
        sections_dict = {
            "brd": project_data.get("brd", ""),
            "srs": project_data.get("srs", ""),
            "use_cases": project_data.get("use_cases", ""),
            "user_stories": project_data.get("user_stories", ""),
            "db_suggestions": project_data.get("db_suggestions", ""),
            "kpis": project_data.get("kpis", ""),
            "workflow": project_data.get("workflow", ""),
            "reports": project_data.get("reports", ""),
        }
        
        if fmt == "PDF":
            data = pdf_export.build_complete_suite_pdf(project_name, industry, timestamp, sections_dict)
        elif fmt == "DOCX":
            data = docx_export.build_complete_suite_docx(
                project_name, industry, timestamp,
                brd=sections_dict["brd"],
                srs=sections_dict["srs"],
                use_cases=sections_dict["use_cases"],
                user_stories=sections_dict["user_stories"],
                db_suggestions=sections_dict["db_suggestions"],
                kpis=sections_dict["kpis"],
                workflow=sections_dict["workflow"],
                reports=sections_dict["reports"],
            )
        elif fmt == "EXCEL":
            data = excel_export.build_complete_suite_excel(project_name, industry, timestamp, sections_dict)
        elif fmt == "MARKDOWN":
            data = markdown_export.build_complete_suite_markdown(project_name, industry, timestamp, sections_dict)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")
            
        return data, file_name, mime

    # ── CASE 2: Single Section Export
    else:
        sec_key = DOC_TYPE_TO_KEY.get(doc_type)
        if not sec_key:
            raise ValueError(f"Invalid document type requested: {doc_type}")
            
        content = project_data.get(sec_key, "")
        doc_label = DOC_KEY_TO_LABEL.get(sec_key, doc_type)
        file_label = doc_type.replace(" ", "")
        
        file_name = f"{clean_proj_name}_{file_label}.{ext}"
        
        if fmt == "PDF":
            data = pdf_export.build_pdf_document(project_name, industry, content, doc_label, timestamp)
        elif fmt == "DOCX":
            data = docx_export.build_section_docx(project_name, industry, sec_key, content, timestamp)
        elif fmt == "EXCEL":
            data = excel_export.build_excel_document(project_name, industry, content, doc_label, timestamp)
        elif fmt == "MARKDOWN":
            # For markdown, build_markdown_document returns string, return it as string or UTF-8 encoded bytes
            data = markdown_export.build_markdown_document(project_name, industry, content, doc_label, timestamp)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")
            
        return data, file_name, mime
