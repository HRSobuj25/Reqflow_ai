import streamlit as st
import pandas as pd
import numpy as np
import time
import json
import io
from datetime import datetime
import plotly.express as px
import prompts
import gemini_service
import database
import docx_export
import pdf_export
import excel_export
import markdown_export
import export_manager
import auth
import importlib
importlib.reload(prompts)
importlib.reload(gemini_service)
importlib.reload(database)
importlib.reload(docx_export)
importlib.reload(pdf_export)
importlib.reload(excel_export)
importlib.reload(markdown_export)
importlib.reload(export_manager)
importlib.reload(auth)

# Try to initialize database tables on startup
if database.DB_AVAILABLE:
    database.create_tables()


# 1. Page Configuration
st.set_page_config(
    page_title="ReqFlow AI - ERP Requirement Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Authentication Routing
auth.init_session_state()
if not st.session_state.user:
    auth.render_login_page()
    st.stop()

# 2. Theme State Management
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

if "credits" not in st.session_state:
    st.session_state.credits = 95

if "projects" not in st.session_state:
    st.session_state.projects = {}

if "current_project" not in st.session_state:
    st.session_state.current_project = None

if "history" not in st.session_state:
    if database.DB_AVAILABLE:
        try:
            st.session_state.history = database.list_projects()
        except Exception:
            st.session_state.history = []
    else:
        st.session_state.history = [
            {"name": "Global Retail Core", "industry": "E-commerce", "date": "Jun 28, 2026"},
            {"name": "MedShield EHR", "industry": "Healthcare", "date": "Jun 27, 2026"},
            {"name": "PayVortex Ledger", "industry": "FinTech", "date": "Jun 25, 2026"}
        ]

# Active page routing — "dashboard" | "history"
if "page" not in st.session_state:
    st.session_state.page = "dashboard"

# Audit callback to log document exports into GeneratedDocuments
def log_download_callback(project_name, document_type, file_format, content):
    if database.DB_AVAILABLE:
        try:
            proj_data = database.get_project_by_name(project_name)
            if proj_data:
                database.log_document_export(
                    project_id=proj_data["id"],
                    document_type=document_type,
                    file_format=file_format,
                    content=content
                )
        except Exception as e:
            print(f"[Database Error] Failed to log document export: {str(e)}")


# Theme Switcher Callback
def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"

IS_DARK = st.session_state.theme == "dark"

# Define theme variables for CSS and charts
bg_color = "#07050f" if IS_DARK else "#faf8ff"
bg_subtle = "#0d0a1b" if IS_DARK else "#f5efff"
card_color = "#110c24" if IS_DARK else "#ffffff"
card_hover = "#171133" if IS_DARK else "#f9f6ff"
border_color = "#271c4c" if IS_DARK else "#e9d5ff"
border_subtle = "#1c1437" if IS_DARK else "#f3ebff"
text_color = "#f4f3f7" if IS_DARK else "#1e1b4b"
text_muted = "#a5b4fc" if IS_DARK else "#4f46e5"
text_dim = "#7c8ba1" if IS_DARK else "#6b7280"
shadow = "none" if IS_DARK else "0 4px 10px rgba(124, 58, 237, 0.08), 0 2px 4px rgba(124, 58, 237, 0.04)"
shadow_lg = "none" if IS_DARK else "0 10px 25px -5px rgba(124, 58, 237, 0.12), 0 8px 10px -6px rgba(124, 58, 237, 0.08)"
gradient_sidebar = "linear-gradient(180deg, #0d0a1c 0%, #05040a 100%)" if IS_DARK else "linear-gradient(180deg, #fbfaff 0%, #f1ebfc 100%)"
sidebar_border = "#1b1432" if IS_DARK else "#e1d4f7"
input_bg = "#161030" if IS_DARK else "#fdfcff"
input_border = "#2f225c" if IS_DARK else "#d8b4fe"
badge_bg = "rgba(139, 92, 246, 0.15)"
badge_color = "#a78bfa" if IS_DARK else "#7c3aed"

# 3. Custom CSS Design System Injection
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Make header container transparent so that child controls like the sidebar collapse button remain visible and functional */
    [data-testid="stAppHeader"], .stAppHeader, section[data-testid="stMain"] header[data-testid="stHeader"] {{
        background-color: transparent !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}

    /* Hide default header menu, deploy buttons, footer and decorations */
    #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], .stDeployButton {{
        display: none !important;
    }}

    /* ============================================================
       SIDEBAR: PERMANENTLY OPEN — no collapse/expand buttons
       Streamlit hides the sidebar by sliding it left with a CSS
       transform (translateX(-290px)). We override that to always
       keep it on-screen and remove every toggle button.
    ============================================================ */

    /* 1. Force sidebar always visible – override Streamlit's slide animation */
    section[data-testid="stSidebar"] {{
        transform: none !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        background: {gradient_sidebar} !important;
        border-right: 1px solid {sidebar_border} !important;
        min-width: 290px !important;
        max-width: 290px !important;
        width: 290px !important;
    }}

    /* 2. Force inner sidebar content visible (Streamlit also fades children) */
    section[data-testid="stSidebar"] > div,
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
        transform: none !important;
        visibility: visible !important;
        opacity: 1 !important;
        display: flex !important;
        flex-direction: column !important;
    }}

    /* 3. Hide ALL sidebar toggle buttons — collapse (inside sidebar) and expand (in header) */
    button[data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stAppHeader"] button,
    div[data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] {{
        display: none !important;
    }}

    /* 4. Ensure the stAppHeader stays transparent and takes zero height so it doesn't push content */
    [data-testid="stAppHeader"], .stAppHeader {{
        height: 0 !important;
        min-height: 0 !important;
        overflow: hidden !important;
    }}

    /* Global reset */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .main, .block-container, section[data-testid="stMain"] {{
        font-family: 'Outfit', sans-serif !important;
    }}
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .main, .block-container, section[data-testid="stMain"] {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
    }}

    /* Main Container Padding */
    .block-container {{
        padding: 1.5rem 2rem 2rem !important;
        max-width: 1440px !important;
    }}
    
    section[data-testid="stSidebar"] .block-container {{
        padding: 1.5rem 1.2rem !important;
    }}

    /* Custom Purple Gradient Text */
    .text-gradient {{
        background: linear-gradient(135deg, #a78bfa 0%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }}

    /* Reusable SaaS Card */
    .saas-card {{
        background-color: {card_color};
        border: 1px solid {border_color};
        border-radius: 14px;
        padding: 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: {shadow};
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    .saas-card:hover {{
        border-color: #8b5cf6;
        box-shadow: {shadow_lg};
        transform: translateY(-2px);
    }}

    .saas-card-title {{
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
        color: {text_color};
        display: flex;
        align-items: center;
        gap: 8px;
    }}
    .saas-card-subtitle {{
        font-size: 0.8rem;
        color: {text_dim};
        margin-bottom: 1.25rem;
    }}

    /* Metric Layout Card */
    .metric-card {{
        background: {card_color};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 1.1rem 1.25rem;
        box-shadow: {shadow};
        position: relative;
        overflow: hidden;
        transition: all 0.2s ease;
    }}
    .metric-card::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(180deg, #8b5cf6 0%, #6366f1 100%);
    }}
    .metric-label {{
        font-size: 0.8rem;
        color: {text_dim};
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    .metric-value {{
        font-size: 1.85rem;
        font-weight: 700;
        color: {text_color};
        margin-top: 0.2rem;
        letter-spacing: -0.02em;
    }}
    .metric-delta {{
        font-size: 0.72rem;
        font-weight: 600;
        margin-top: 0.3rem;
        display: inline-flex;
        align-items: center;
        gap: 3px;
        padding: 2px 6px;
        border-radius: 4px;
    }}
    .delta-up {{
        color: {"#10b981" if IS_DARK else "#059669"};
        background: {"rgba(16, 185, 129, 0.12)" if IS_DARK else "rgba(5, 150, 105, 0.08)"};
    }}
    .delta-down {{
        color: {"#ef4444" if IS_DARK else "#dc2626"};
        background: {"rgba(239, 68, 68, 0.12)" if IS_DARK else "rgba(220, 38, 38, 0.08)"};
    }}

    /* Forms and Input Fields */
    div[data-testid="stTextInput"] input, 
    div[data-testid="stTextArea"] textarea,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        color: {text_color} !important;
        border-radius: 10px !important;
        font-family: 'Cambria', Georgia, serif !important;
        transition: all 0.2s ease-in-out !important;
    }}
    div[data-testid="stTextInput"] input:focus, 
    div[data-testid="stTextArea"] textarea:focus,
    div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within {{
        border-color: #8b5cf6 !important;
        box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.15) !important;
    }}
    
    label[data-testid="stWidgetLabel"] p {{
        font-weight: 600 !important;
        color: {text_color} !important;
        font-size: 0.88rem !important;
        margin-bottom: 0.3rem !important;
    }}

    /* Multiselect overrides */
    div[data-testid="stMultiSelect"] div[data-baseweb="select"] {{
        background-color: {input_bg} !important;
        border: 1px solid {input_border} !important;
        border-radius: 10px !important;
    }}
    span[data-baseweb="tag"] {{
        background-color: #8b5cf6 !important;
        color: #ffffff !important;
        border-radius: 6px !important;
    }}

    /* Action & Interactive Buttons styling */
    div.stButton > button, div.stDownloadButton > button, div[data-testid="stDownloadButton"] button {{
        background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%) !important;
        color: #ffffff !important;
        border: none !important;
        padding: 0.65rem 1.25rem !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        width: 100% !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 14px rgba(139, 92, 246, 0.25) !important;
        font-family: 'Cambria', Georgia, serif !important;
    }}
    div.stButton > button:hover, div.stDownloadButton > button:hover, div[data-testid="stDownloadButton"] button:hover {{
        background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%) !important;
        color: #ffffff !important;
        transform: translateY(-1.5px) !important;
        box-shadow: 0 6px 18px rgba(139, 92, 246, 0.35) !important;
    }}
    div.stButton > button:active, div.stDownloadButton > button:active, div[data-testid="stDownloadButton"] button:active {{
        transform: translateY(0) !important;
    }}

    /* Secondary/Theme toggle button override */
    div[data-testid="stSidebar"] div.stButton > button {{
        background: transparent !important;
        border: 1px solid {border_color} !important;
        color: {text_color} !important;
        box-shadow: none !important;
        font-size: 0.85rem !important;
        padding: 0.45rem 1rem !important;
    }}
    div[data-testid="stSidebar"] div.stButton > button:hover {{
        background: {card_hover} !important;
        border-color: #8b5cf6 !important;
    }}

    /* Tabs Styling */
    button[data-baseweb="tab"] {{
        background: transparent !important;
        color: {text_dim} !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.1rem !important;
        border: 1px solid transparent !important;
        border-radius: 8px !important;
        font-family: 'Cambria', Georgia, serif !important;
        transition: all 0.2s ease !important;
    }}
    button[data-baseweb="tab"]:hover {{
        color: #8b5cf6 !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: #ffffff !important;
        background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%) !important;
        box-shadow: 0 4px 10px rgba(139, 92, 246, 0.2) !important;
    }}
    [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{
        display: none !important;
    }}
    [data-baseweb="tab-list"] {{
        gap: 5px !important;
        background: {bg_subtle} !important;
        border: 1px solid {border_color} !important;
        border-radius: 11px !important;
        padding: 4px !important;
        margin-bottom: 1.25rem !important;
    }}

    /* Custom Badges */
    .saas-badge {{
        display: inline-flex;
        align-items: center;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 600;
        gap: 5px;
    }}
    .saas-badge-purple {{
        background-color: rgba(139, 92, 246, 0.12);
        color: #c084fc;
        border: 1px solid rgba(139, 92, 246, 0.25);
    }}
    .saas-badge-green {{
        background-color: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.25);
    }}

    /* Table styling */
    .saas-table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 1rem;
        font-size: 0.85rem;
    }}
    .saas-table th {{
        text-align: left;
        padding: 0.75rem 1rem;
        color: {text_muted};
        border-bottom: 2px solid {border_color};
        font-weight: 600;
    }}
    .saas-table td {{
        padding: 0.75rem 1rem;
        color: {text_color};
        border-bottom: 1px solid {border_subtle};
    }}
    .saas-table tr:hover {{
        background-color: {card_hover};
    }}

    /* Empty/Placeholder States */
    .empty-state {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 4.5rem 2rem;
        border: 2px dashed {border_color};
        border-radius: 16px;
        text-align: center;
        background-color: {card_color};
    }}
    .empty-state-icon {{
        font-size: 3.5rem;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #a78bfa 0%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: float 4s ease-in-out infinite;
    }}
    @keyframes float {{
        0% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-8px); }}
        100% {{ transform: translateY(0px); }}
    }}

    /* Form Card Border Highlight */
    .form-container {{
        border-left: 4px solid #8b5cf6 !important;
    }}

    /* Sidebar Logo */
    .sidebar-logo {{
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 0.5rem 0.25rem;
        margin-bottom: 1.5rem;
    }}
    .logo-badge {{
        background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
        color: white;
        border-radius: 8px;
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        box-shadow: 0 4px 10px rgba(139, 92, 246, 0.3);
    }}
    .logo-text {{
        font-size: 1.25rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: {text_color};
    }}

    /* History and navigation elements in Sidebar */
    .sidebar-heading {{
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        color: {text_dim};
        letter-spacing: 0.08em;
        margin: 1.5rem 0 0.5rem 0.25rem;
    }}
    
    .history-item {{
        display: flex;
        flex-direction: column;
        padding: 0.55rem 0.75rem;
        border-radius: 8px;
        cursor: pointer;
        margin-bottom: 0.35rem;
        border: 1px solid transparent;
        transition: all 0.2s ease;
    }}
    .history-item:hover {{
        background-color: {card_hover};
        border-color: {border_subtle};
    }}
    .history-name {{
        font-size: 0.85rem;
        font-weight: 600;
        color: {text_color};
    }}
    .history-meta {{
        font-size: 0.72rem;
        color: {text_dim};
        display: flex;
        justify-content: space-between;
        margin-top: 0.15rem;
    }}
    
    .credit-box {{
        background: rgba(139, 92, 246, 0.08);
        border: 1px solid rgba(139, 92, 246, 0.2);
        border-radius: 10px;
        padding: 0.85rem;
        margin-top: 2rem;
    }}
    .credit-title {{
        font-size: 0.78rem;
        font-weight: 600;
        color: {text_muted};
    }}
    .credit-progress {{
        height: 6px;
        background: {border_subtle};
        border-radius: 3px;
        margin: 0.5rem 0 0.35rem 0;
        overflow: hidden;
    }}
    .credit-fill {{
        height: 100%;
        background: linear-gradient(90deg, #8b5cf6 0%, #6366f1 100%);
        border-radius: 3px;
    }}
    .credit-foot {{
        font-size: 0.72rem;
        color: {text_dim};
        display: flex;
        justify-content: space-between;
    }}
</style>
""", unsafe_allow_html=True)

# 4. High-Fidelity Mock Generator Database/Templates
INDUSTRIES = {
    "FinTech": {
        "features": ["Double-entry Ledger", "Automated Reconciliation", "Fraud Risk Scoring", "Payment Gateway API", "PCI-DSS Audit Logs", "Multi-currency Wallet"],
        "default_scope": "Create a robust FinTech middleware system to route settlements, maintain audit ledgers, and score transactions for fraud potential in high-volume environments.",
        "kpi_metrics": {"total_requirements": "34 Detailed Items", "avg_complexity": "High (M3-M5)", "compliance_grade": "PCI-DSS / SOC 2 Ready"},
        "brd": """
# Business Requirements Document (BRD)
## 1. Project Overview & Context
This Business Requirements Document outlines the core operations, user journeys, and target goals for **{project_name}** in the **FinTech** domain.
The platform will act as an enterprise ledger system executing secure payment orchestration and ledger settlements.

### 1.1 Business Goals & Success Metrics
- **Automate Audit Readiness:** Reduce manual verification tasks by 92% and speed up monthly ledger closures.
- **Minimize Transaction Friction:** Settle double-entry ledger items in under 200ms at scale.
- **Ensure Full Security Compliance:** Maintain end-to-end data safety covering PCI-DSS level 1, GDPR right-to-forget ledger exceptions, and AML/KYC guidelines.

### 1.2 Target Stakeholders & Actors
- **Chief Financial Officer (CFO):** Tracks treasury and ledger health, accesses reconciliation reports.
- **Compliance Auditor:** Inspects immutable ledger entries, fraud alert logs, and system access history.
- **Finance Operations Manager:** Manages merchant settlements, manual reviews of fraud alerts, and currency parameters.

## 2. Business Process Workflow
Below is the core business process workflow illustrating transaction flow, fraud vetting, and ledger logging:

```mermaid
graph TD
    A[Checkout Transaction Request] --> B[Decoupled API Gate]
    B --> C{{ML Fraud Scoring Service}}
    C -- Score >= 0.85 (Critical) --> D[Flag Transaction & Trigger Manual Review]
    C -- Score < 0.85 (Pass) --> E[Double-entry Balance Check]
    E -- Sufficient Funds --> F[Execute Ledger Settlement]
    E -- Insufficient Funds --> G[Raise Ledger Exception & Deny Transaction]
    F --> H[Compile Reconciliation Summary & PDF Invoice]
```

## 3. Scope of Requirements
The scope of **{project_name}** covers the following core capabilities:
- **Ledger Ingestion & Double-entry Balancing:** Guarantees that every credit has an equal debit.
- **Automated Fraud Scoring Engine:** Runs real-time evaluation against transaction behavior signatures.
- **Multi-currency Clearinghouse:** Dynamically routes settlements across selected assets.

### 3.1 Custom Scope Context
*{scope_details}*
        """,
        "srs": """
# Software Requirements Specification (SRS)
## 1. Functional Requirements

### 1.1 Transaction Processing Engine
- **Req-F-1.1.1 (Double-Entry Ledger):** The system must execute balance operations as unified SQL transactions. Every transaction debit must balance with a matching credit.
- **Req-F-1.1.2 (Multi-currency Conversion):** The multi-currency routing module must fetch exchange rates every 15 minutes and calculate conversions with 4 decimal points accuracy.
- **Req-F-1.1.3 (Reconciliation Automation):** Daily ledger summaries must run automatically at 00:00 UTC, matching gateway events to ledger records.

### 1.2 Fraud & Risk Assessment
- **Req-F-1.2.1 (Scoring Threshold):** Every transaction must go through the ML engine. High risk transactions (anomaly rating > 0.85) must be paused.
- **Req-F-1.2.2 (Multi-factor Verification):** Settlements exceeding $10,000 must request secondary biometrics/OTP confirmation before final commitment.

## 2. Non-Functional Requirements

### 2.1 Security & Compliance
- **Compliance Assurance:** Implement AES-256 field-level encryption for all PII data and encrypt connection channels using TLS 1.3.
- **Immutable Log Trails:** All logs documenting administrative settings and overrides must be written to an immutable append-only storage tier.

### 2.2 Performance & Scalability
- **Transaction Throughput:** Scalable backend hosting capable of handling 5,000 write operations per second (TPS) peak.
- **Availability:** Maintain 99.999% availability for key routing APIs.
        """,
        "use_cases": """
# Use Case Specifications

The table below catalogs primary operational use cases mapped to user paths:

| Use Case ID | Use Case Name | Actor | Preconditions | Postconditions |
| :--- | :--- | :--- | :--- | :--- |
| **UC-FT-101** | Process Double-Entry Settlement | Client Gateway | API authentication validated | Ledger balance updated, receipt dispatched |
| **UC-FT-102** | Flag Fraudulent Anomaly | Risk Engine | Transaction details ingested | Transaction state set to 'Hold', compliance alert sent |
| **UC-FT-103** | Auto-Reconcile Invoices | Cron Scheduler | Day close triggered (00:00 UTC) | Exception logs generated, reconciliation report locked |

### Use Case Flow: UC-FT-101 (Process Double-Entry Settlement)
1. Merchant app initiates a POST request to `/api/v1/settle` containing source, destination, currency, and amount.
2. The middleware system triggers API security token validation.
3. System verifies that the source account balance meets the settlement amount.
4. Transaction ledger record is generated as an atomic database write:
   - Debit: Source account balance decreased by amount.
   - Credit: Destination account balance increased by amount.
5. System returns status `201 Created` with ledger hash.
        """,
        "user_stories": """
# User Stories & Acceptance Criteria

### US-FT-201: Multi-Currency Support for Merchants
**As a** Merchant Operations Director  
**I want to** settle transaction settlements directly in EUR, USD, and GBP  
**So that** we prevent foreign exchange conversion fees during cross-border operations.

*Acceptance Criteria:*
- **AC1:** Merchant can select active currency wallets from the control panel.
- **AC2:** Settlements are directly sent to the wallet of matching currency without converting.
- **AC3:** Exchange conversion charges are calculated and displayed dynamically for mixed-wallets.

---

### US-FT-202: Automated Transaction Reconciliation
**As a** Corporate Accountant  
**I want to** receive automatic daily mismatch alerts between settlement reports and bank files  
**So that** I don't have to manually verify thousands of bank ledgers every morning.

*Acceptance Criteria:*
- **AC1:** Daily comparison matches bank ledger uploads to internal ledger records.
- **AC2:** Entries with difference > $0.01 are sent to the Exception queue.
- **AC3:** Reconciled matches are labeled with a green badge automatically.
        """,
        "db_suggestions": """
# Database Design Suggestions

Suggested stack: **PostgreSQL** (due to strong ACID transaction capabilities) with read replicas for compliance logs.

## Entity Relationship Outline
```mermaid
erDiagram
    WALLETS ||--o{ TRANSACTIONS : debit_wallet
    WALLETS ||--o{ TRANSACTIONS : credit_wallet
    TRANSACTIONS ||--|| RECONCILIATION_LOGS : reconciles
```

## SQL DDL Scripts
The following SQL script models the database core tables:

```sql
-- Core Accounts / Wallets Table
CREATE TABLE wallets (
    wallet_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id VARCHAR(100) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    balance NUMERIC(18, 4) NOT NULL DEFAULT 0.0000,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Immutable Ledger Table
CREATE TABLE ledger_transactions (
    tx_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_wallet_id UUID REFERENCES wallets(wallet_id),
    dest_wallet_id UUID REFERENCES wallets(wallet_id),
    amount NUMERIC(18, 4) NOT NULL CHECK (amount > 0),
    currency VARCHAR(3) NOT NULL,
    tx_status VARCHAR(20) DEFAULT 'pending',
    security_hash VARCHAR(64) UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexing for high-speed ledger searches
CREATE INDEX idx_ledger_source ON ledger_transactions(source_wallet_id);
CREATE INDEX idx_ledger_dest ON ledger_transactions(dest_wallet_id);
```
        """
    },
    "E-commerce": {
        "features": ["Product Catalog", "Shopping Cart", "Inventory Sync", "Order Fulfillment Engine", "Discount & Promo Rules", "Customer Reviews Platform"],
        "default_scope": "Design a scalable E-commerce store engine supporting catalog queries, cart workflows, checkout processing, and real-time inventory updates across warehouses.",
        "kpi_metrics": {"total_requirements": "28 Detailed Items", "avg_complexity": "Medium (M2-M4)", "compliance_grade": "GDPR / CCPA Compliant"},
        "brd": """
# Business Requirements Document (BRD)
## 1. Project Overview & Context
This BRD defines the features and objectives for **{project_name}** in the **E-commerce** space. The system processes inventory states, customer shopping carts, checkout settlements, and order dispatch workflows.

### 1.1 Business Goals & Success Metrics
- **Increase Conversion Rates:** Minimize shopping cart abandonment by keeping checkout steps under 3 clicks.
- **Maintain Real-time Inventory Sync:** Sync product volumes across multiple online storefronts and warehouse points in under 1 second.
- **Enhance Operational Scalability:** Handle multi-warehouse fulfillment and automate carrier assignment.

### 1.2 Core Customer Segment
- **Online Shoppers:** Seek lightning-fast catalog search, review systems, and easy checkout.
- **Inventory Managers:** Monitor warehouse stock levels, assign low-stock alert thresholds.
- **Marketing Admins:** Create discount rules, launch coupon code campaigns.

## 2. Business Process Workflow
Below is the transactional checkout and inventory allocation sequence:

```mermaid
graph TD
    A[Customer Checkout Action] --> B{{Check Inventory Availability}}
    B -- Stock Available --> C[Lock Inventory Item & Process Payment]
    B -- Out of Stock --> D[Notify Customer & Suggest Backorder]
    C --> E[Generate Warehouse Packing list]
    E --> F[Assign Shipping Carrier]
    F --> G[Email Shipping Label & Tracking Code]
```

## 3. Scope of Requirements
The scope of **{project_name}** covers the following systems:
- **Product Catalog Management:** Real-time search engine optimization, category structures.
- **Order Fulfillment Pipeline:** Automatic stock allocation, label creation.
- **Promo Rule Engine:** Code validate algorithms, discount triggers.

### 3.1 Custom Scope Context
*{scope_details}*
        """,
        "srs": """
# Software Requirements Specification (SRS)
## 1. Functional Requirements

### 1.1 Catalog & Cart System
- **Req-EC-1.1.1 (Instant Catalog Search):** Catalog query search response must return matches in less than 150ms using indexing tools (ElasticSearch/OpenSearch).
- **Req-EC-1.1.2 (Persistent Carts):** Customer shopping carts must be saved for anonymous guests for up to 30 days.

### 1.2 Inventory & Checkout
- **Req-EC-1.2.1 (Inventory Locks):** System must lock items in the cart for 10 minutes once checkout is initiated to prevent over-selling.
- **Req-EC-1.2.2 (Discount Validation):** Promotional discount codes must validate pricing synchronously before final payment submission.

## 2. Non-Functional Requirements

### 2.1 Scalability & Security
- **Peak Loads:** Auto-scale API servers during traffic events (e.g., Black Friday) up to 20x average loads.
- **Privacy Compliance:** Secure storage of profiles in compliance with GDPR guidelines.
        """,
        "use_cases": """
# Use Case Specifications

| Use Case ID | Use Case Name | Actor | Preconditions | Postconditions |
| :--- | :--- | :--- | :--- | :--- |
| **UC-EC-201** | Add Item to Shopping Cart | Shopper | Catalog details loaded | Cart updated, stock allocation locked |
| **UC-EC-202** | Validate Promo Discount | Shopper | Cart total > 0 | Total price discounted, coupon code validated |
| **UC-EC-203** | Dispatch Warehouse Packing Alert | Fulfillment Operator | Payment verification completed | Package registered, courier assigned |

### Use Case Flow: UC-EC-201 (Add Item to Shopping Cart)
1. Customer clicks "Add to Cart" on a product detail page.
2. System queries database to verify current inventory > 0.
3. System inserts/updates active cart row with selected product.
4. Product inventory is temporarily locked in cache (Redis) for 10 minutes.
5. Cart total is recalculated and updated dynamically on the frontend.
        """,
        "user_stories": """
# User Stories & Acceptance Criteria

### US-EC-301: Dynamic Promotions Engine
**As an** Online Marketing Specialist  
**I want to** configure "Buy One Get One (BOGO)" rules for selective categories  
**So that** I can boost slow inventory turnover rates during holiday seasons.

*Acceptance Criteria:*
- **AC1:** Administrator can define discount duration, categories, and minimum items.
- **AC2:** Cart automatically applies discount when items matching the rule are included.
- **AC3:** Only one category promotion can be applied per order.

---

### US-EC-302: Single-Page Checkout Journey
**As a** Returning Customer  
**I want to** load my saved address and credit card details securely  
**So that** I can complete my purchase in one click.

*Acceptance Criteria:*
- **AC1:** Shipping profiles are encrypted and tokenized.
- **AC2:** Checkout page displays order summaries clearly on a single UI screen.
- **AC3:** Payment processing runs asynchronously with a spinner interface.
        """,
        "db_suggestions": """
# Database Design Suggestions

Suggested stack: **PostgreSQL or MySQL** for core transactions, paired with **Redis** for cart storage and product search caching.

## Entity Relationship Outline
```mermaid
erDiagram
    PRODUCTS ||--o{ ORDER_ITEMS : contains
    ORDERS ||--o{ ORDER_ITEMS : lists
    USERS ||--o{ ORDERS : places
```

## SQL DDL Scripts
Core schema mapping order transactions:

```sql
-- Product Catalog Configuration
CREATE TABLE products (
    product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku VARCHAR(50) UNIQUE NOT NULL,
    title VARCHAR(200) NOT NULL,
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    stock_quantity INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Core Orders Table
CREATE TABLE orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL,
    subtotal NUMERIC(10, 2) NOT NULL,
    tax NUMERIC(10, 2) DEFAULT 0.00,
    order_status VARCHAR(30) DEFAULT 'received',
    shipping_address TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Order Items Detail
CREATE TABLE order_items (
    order_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(product_id),
    quantity INT NOT NULL CHECK (quantity > 0),
    price_at_purchase NUMERIC(10, 2) NOT NULL
);
```
        """
    },
    "Healthcare": {
        "features": ["HIPAA Patient Records", "Appointment Scheduler", "Telehealth Video SDK", "Insurance Claims Portal", "E-Prescription (e-Rx)", "Doctor Scheduling"],
        "default_scope": "Develop a secure EHR and clinical dashboard to schedule patient visits, transmit electronic prescriptions, and submit insurance claims with high compliance controls.",
        "kpi_metrics": {"total_requirements": "40 Detailed Items", "avg_complexity": "Critical (M4-M5)", "compliance_grade": "HIPAA / HITRUST Compliant"},
        "brd": """
# Business Requirements Document (BRD)
## 1. Project Overview & Context
This document defines requirements for **{project_name}**, a secure cloud ERP serving **Healthcare** clinics and patient portals.
It manages Electronic Health Records (EHR), physician appointment calendars, and billing/claims pipelines.

### 1.1 Business Goals & Success Metrics
- **Enhance Patient Portal Utility:** Lower clinic reception burdens by moving 80% of scheduling online.
- **HIPAA Regulatory Adherence:** Eliminate audit issues by establishing 100% encrypted, logged, and role-restricted healthcare data workflows.
- **Accelerate Claim Processing:** Standardize insurance billing output formats to reduce claim rejection rates below 5%.

### 1.2 Target Stakeholders & Actors
- **Clinic Administrator:** Coordinates physician timetables, reviews clinic billing performance.
- **Physician / Nurse Practitioner:** Evaluates patient histories, submits e-Prescriptions during consultation.
- **Patient:** books consultations, logs wellness metrics, views prescription records.

## 2. Clinical Workflow Diagram
Process workflow covering consultations, medical charting, and insurance billing actions:

```mermaid
graph TD
    A[Patient Schedules Consultation] --> B[Doctor Conducts Session]
    B --> C[Doctor Writes EHR chart & e-Rx]
    C --> D[e-Rx sent to Pharmacy API]
    C --> E[Submit Billing Codes to Claims Portal]
    E --> F{{Claims Validation Check}}
    F -- Approved --> G[Insurance Settlement Received]
    F -- Rejected --> H[Admin Claim Review Queue]
```

## 3. Scope of Requirements
The scope of **{project_name}** covers the following systems:
- **Protected Health Records (PHI):** Strictly controlled patient files.
- **Doctor Calendars & Schedulers:** Real-time scheduling modules.
- **Secure Telehealth Interface:** Integrated Video SDK.

### 3.1 Custom Scope Context
*{scope_details}*
        """,
        "srs": """
# Software Requirements Specification (SRS)
## 1. Functional Requirements

### 1.1 HIPAA Clinical Documentation
- **Req-HC-1.1.1 (Access Auditing):** Every access attempt (read/write) to PHI data must be written to an audit log. The audit log must not be modifiable even by super-users.
- **Req-HC-1.1.2 (E-prescriptions):** The system must interface with external pharmacy networks (Surescripts) for electronic transmissions.

### 1.2 Appointment Scheduling
- **Req-HC-1.2.1 (Conflict Prevention):** Calendars must prevent double-booking timeslots for the same physician.

## 2. Non-Functional Requirements

### 2.1 Security & Compliance
- **Data Encryption:** Enforce AES-256 field-level encryption for patient names, birthdates, and notes.
- **Timeout Restrictions:** Automatically log users out of terminal screens after 5 minutes of idle time.
        """,
        "use_cases": """
# Use Case Specifications

| Use Case ID | Use Case Name | Actor | Preconditions | Postconditions |
| :--- | :--- | :--- | :--- | :--- |
| **UC-HC-301** | Create Electronic Prescription | Physician | Patient EHR active, Doctor authorized | e-Rx signed, dispatched to pharmacy |
| **UC-HC-302** | Submit Medical Claim | Billing Clerk | Consultation complete, ICD-10 code added | Claim submitted, status tracker initialized |
| **UC-HC-303** | Auto-Assign Room Schedule | Intake Nurse | Patient check-in logged | Room occupied, scheduler updated |

### Use Case Flow: UC-HC-301 (Create Electronic Prescription)
1. Doctor selects "Create Prescription" within patient EHR layout.
2. System displays search dialog to find active medications.
3. Doctor selects medication, inputs dosage directions, and reviews drug-drug interaction warnings.
4. Doctor inputs their authorized e-Signature PIN.
5. System transmits XML-packaged prescription to the target pharmacy API.
        """,
        "user_stories": """
# User Stories & Acceptance Criteria

### US-HC-401: EHR Access Audit Trails
**As a** Clinic Chief Compliance Officer  
**I want to** view a detailed history of every user who viewed patient record files  
**So that** we pass HIPAA compliance checks and audit data leaks.

*Acceptance Criteria:*
- **AC1:** Log captures timestamp, user ID, patient ID, and action (read/write).
- **AC2:** Audit logs cannot be deleted or edited.
- **AC3:** Compliance officer can filter logs by patient name or date range.

---

### US-HC-402: Auto-Verification of Insurance Benefits
**As a** Clinic Front Desk Receptionist  
**I want to** automatically check if a patient's insurance is active when scheduling a consultation  
**So that** we guarantee billing coverage prior to clinical sessions.

*Acceptance Criteria:*
- **AC1:** Benefit verification runs API lookup against major clearinghouses (270/271 eligibility transaction).
- **AC2:** Results display within 5 seconds as an indicator badge (Approved/Rejected/Unknown).
- **AC3:** Deductible amount details are automatically saved in the billing module.
        """,
        "db_suggestions": """
# Database Design Suggestions

Suggested stack: **PostgreSQL** with Row-Level Security (RLS) policies activated to enforce medical data isolation, coupled with **GCP Cloud KMS** for database keys management.

## Entity Relationship Outline
```mermaid
erDiagram
    PATIENTS ||--o{ MEDICAL_RECORDS : historical_logs
    PRACTITIONERS ||--o{ APPOINTMENTS : books
    PATIENTS ||--o{ APPOINTMENTS : schedules
```

## SQL DDL Scripts
Database schema mapping clinical parameters:

```sql
-- Patients Demographic Storage
CREATE TABLE patients (
    patient_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name BYTEA NOT NULL, -- Encrypted Field
    last_name BYTEA NOT NULL,  -- Encrypted Field
    date_of_birth BYTEA NOT NULL, -- Encrypted Field
    insurance_policy VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- EHR Documents Table
CREATE TABLE clinical_records (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(patient_id) ON DELETE CASCADE,
    physician_id UUID NOT NULL,
    consultation_notes TEXT NOT NULL,
    icd10_codes VARCHAR(15)[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- HIPAA Access Audit Log Table
CREATE TABLE ehr_access_logs (
    log_id BIGSERIAL PRIMARY KEY,
    operator_id UUID NOT NULL,
    patient_id UUID REFERENCES patients(patient_id),
    action_type VARCHAR(10) NOT NULL, -- 'READ' or 'WRITE'
    access_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```
        """
    },
    "Supply Chain": {
        "features": ["Warehouse Space Tracker", "IoT Fleet GPS", "Shipment Optimization", "Purchase Orders ERP", "Supplier Catalog", "Demand Forecast Engine"],
        "default_scope": "Build a supply chain operations console to manage warehouse inventory quantities, assign shipments to delivery routes, and track vehicle GPS details.",
        "kpi_metrics": {"total_requirements": "30 Detailed Items", "avg_complexity": "Medium (M3-M4)", "compliance_grade": "ISO 9001 / WMS Ready"},
        "brd": """
# Business Requirements Document (BRD)
## 1. Project Overview & Context
This document specifies the logistics tracking controls for **{project_name}** in the **Supply Chain & Logistics** industry.
The software manages fleet metrics, warehouse storage bins, routing updates, and purchase requisition details.

### 1.1 Business Goals & Success Metrics
- **Optimize Transit Logistics:** Reduce fuel expenses by 14% via automated GPS routing.
- **Maximize Warehouse Storage:** Dynamically track pallet placements, keeping utilization above 90%.
- **Secure Procurement Chains:** Track vendor compliance, cataloging lead-time histories.

### 1.2 Core Operational Roles
- **Logistics Dispatcher:** Plans transit routes, monitors delivery vehicles.
- **Warehouse Manager:** Scans incoming crates, manages stock placement.
- **Procurement Officer:** Issues purchase orders to vetted suppliers.

## 2. Supply Chain Flow
Logistics workflow covering supplier inventory intake and transit:

```mermaid
graph TD
    A[Supplier Dispatches Goods] --> B[Warehouse Scanning & Receipt]
    B --> C[Bin Allocation Algorithm]
    C --> D[Stock Levels Update ERP]
    D --> E{{Order Demands Check}}
    E -- Stock Available --> F[Pick, Pack & Load Fleet]
    F --> G[IoT Real-time GPS Tracking]
    G --> H[Final Delivery Confirmation]
```

## 3. Scope of Requirements
The scope of **{project_name}** covers the following systems:
- **Warehouse Bin Allocation (WMS):** Pallet coordinates storage.
- **IoT Transit Monitoring:** GPS coordination logs.
- **Procurement Workflows:** Supplier catalogs.

### 3.1 Custom Scope Context
*{scope_details}*
        """,
        "srs": """
# Software Requirements Specification (SRS)
## 1. Functional Requirements

### 1.1 WMS Tracking
- **Req-SC-1.1.1 (Storage Allocation):** Storage slot calculation must run dynamically when pallets are checked in, choosing the optimal bin based on size/weight.
- **Req-SC-1.1.2 (Stock Alerting):** Automatically issue procurement requisitions when inventory drops below safety thresholds.

### 1.2 Transit Monitoring
- **Req-SC-1.2.1 (Fleet Tracking):** IoT sensors must transmit latitude/longitude parameters to the console every 30 seconds.

## 2. Non-Functional Requirements

### 2.1 Performance & Reliability
- **Offline Capabilities:** Warehouse handheld scanning devices must buffer updates locally during network drops.
        """,
        "use_cases": """
# Use Case Specifications

| Use Case ID | Use Case Name | Actor | Preconditions | Postconditions |
| :--- | :--- | :--- | :--- | :--- |
| **UC-SC-401** | Allocate Bin Storage Slot | Warehouse Operator | Crate barcode scanned | Bin reserved, stock allocated |
| **UC-SC-402** | Optimize Delivery Route | Route Optimizer | Fleet assigned, cargo loaded | Waypoints mapped to vehicle GPS console |
| **UC-SC-403** | Issue Automated PO | Procurement Engine | Stock level < threshold | PO sent to vendor, pending review status |

### Use Case Flow: UC-SC-401 (Allocate Bin Storage Slot)
1. Forklift operator scans crate bar-code using warehouse scanner.
2. Scanner API verifies product type, hazardous tags, and weight.
3. System runs bin allocation search to find matching empty rack space.
4. Rack space code is displayed on handheld screen with navigation path.
5. Operator places crate and scans rack barcode to confirm.
        """,
        "user_stories": """
# User Stories & Acceptance Criteria

### US-SC-501: Live Fleet Map View
**As a** Dispatch Coordinator  
**I want to** view all trucks as markers on an interactive map  
**So that** I can redirect vehicles during traffic delays.

*Acceptance Criteria:*
- **AC1:** Map updates truck coordinates every 60 seconds.
- **AC2:** Truck marker is colored green (active), orange (delay), or grey (parked).
- **AC3:** Clicking a truck marker displays driver detail and manifest contents.

---

### US-SC-502: Automated Procurement Limits
**As a** Procurement Manager  
**I want to** establish rule-based ordering limits for suppliers  
**So that** I don't have to manually sign off on low-cost stock orders.

*Acceptance Criteria:*
- **AC1:** Reorder rules automatically issue PO for approvals < $5,000.
- **AC2:** System aggregates orders weekly to minimize shipping fees.
- **AC3:** PO details are automatically emailed to supplier contact.
        """,
        "db_suggestions": """
# Database Design Suggestions

Suggested stack: **PostgreSQL** with **PostGIS extension** (for GPS coordinates and map query calculations).

## Entity Relationship Outline
```mermaid
erDiagram
    WAREHOUSES ||--o{ BINS : contains
    BINS ||--o{ STOCK_ITEMS : stores
    VEHICLES ||--o{ SHIPMENTS : delivers
```

## SQL DDL Scripts
Database schema mapping supply chain records:

```sql
-- Warehouses Structure
CREATE TABLE warehouses (
    warehouse_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    facility_name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    max_weight_capacity NUMERIC(12, 2) NOT NULL
);

-- Warehouse Rack Storage Bins
CREATE TABLE storage_bins (
    bin_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    warehouse_id UUID REFERENCES warehouses(warehouse_id),
    aisle_row_level VARCHAR(20) NOT NULL,
    is_occupied BOOLEAN DEFAULT FALSE,
    max_payload INT NOT NULL
);

-- IoT Vehicle Logs Table
CREATE TABLE vehicle_telemetry (
    log_id BIGSERIAL PRIMARY KEY,
    vehicle_identifier VARCHAR(30) NOT NULL,
    latitude NUMERIC(9, 6) NOT NULL,
    longitude NUMERIC(9, 6) NOT NULL,
    speed_kph NUMERIC(5, 2),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_telemetry_time ON vehicle_telemetry(timestamp);
```
        """
    },
    "EdTech": {
        "features": ["Student Information (SIS)", "LMS Course Catalog", "Online Exam Lockdown", "Automated Gradebook", "Zoom/Video API integration", "Parent Portal Alerts"],
        "default_scope": "Design a comprehensive school ERP containing student profiles, virtual classrooms, course structures, and automated exam grading options.",
        "kpi_metrics": {"total_requirements": "26 Detailed Items", "avg_complexity": "Low (M1-M3)", "compliance_grade": "FERPA / COPPA Compliant"},
        "brd": """
# Business Requirements Document (BRD)
## 1. Project Overview & Context
This document specifies the academic portal features for **{project_name}** in the **EdTech** sector.
The application coordinates virtual classes, registers enrollments, and compiles report cards.

### 1.1 Business Goals & Success Metrics
- **Automate Grading Operations:** Decrease assignment review times by 40% using automated gradebooks.
- **Increase Parent Involvement:** Boost communication channels by sending real-time SMS/Email course alerts.
- **Maintain Compliance standards:** Ensure student database rules strictly follow FERPA security policies.

### 1.2 Target Stakeholders & Actors
- **School Registrar:** Sets school term structures, monitors enrollment logs.
- **Teacher:** Designs class materials, administers tests, grades assignments.
- **Student & Parent:** Views class schedules, completes assignments, reviews grading scores.

## 2. EdTech Core Workflow
Process sequence covering course enrollment, assignment completion, and gradebooks:

```mermaid
graph TD
    A[Student Registers for Course] --> B[Teacher Uploads Assignment]
    B --> C[Student Completes Submission]
    C --> D{{Auto-Grading Check}}
    D -- MCQ/Standardized --> E[Auto-grade & Update Gradebook]
    D -- Project/Essay --> F[Flag for Teacher Manual Grading]
    E --> G[Publish Grade to Student Portal]
    F --> G
    G --> H[Email Grade summary to Parents]
```

## 3. Scope of Requirements
The scope of **{project_name}** covers the following systems:
- **LMS Course Catalog:** Video portals and file storage.
- **SIS Registries:** Student profile details.
- **Gradebooks:** Weighted grading schemes.

### 3.1 Custom Scope Context
*{scope_details}*
        """,
        "srs": """
# Software Requirements Specification (SRS)
## 1. Functional Requirements

### 1.1 LMS & Assignment Workflow
- **Req-ED-1.1.1 (Assignment Submission):** The platform must accept file attachments up to 100MB for submissions.
- **Req-ED-1.1.2 (Plagiarism Scanner):** Course submissions must run through plagiarism APIs prior to teacher routing.

### 1.2 SIS & Grading
- **Req-ED-1.2.1 (FERPA isolation):** Gradebooks must not be exposed to unauthorized users.

## 2. Non-Functional Requirements

### 2.1 Security & Compliance
- **Data Protection:** Implement strict access control lists (ACL) separating parents, students, and teachers.
        """,
        "use_cases": """
# Use Case Specifications

| Use Case ID | Use Case Name | Actor | Preconditions | Postconditions |
| :--- | :--- | :--- | :--- | :--- |
| **UC-ED-501** | Submit Semester Assignment | Student | Course enrolled, assignment published | Assignment file logged, grader alerted |
| **UC-ED-502** | Input Student Grades | Teacher | Assignment deadline passed | Student grade updated in gradebook |
| **UC-ED-503** | Trigger Parent Alert | SMS Engine | Grade published < threshold | SMS notification sent to registered parent |

### Use Case Flow: UC-ED-501 (Submit Semester Assignment)
1. Student navigates to the assignment page in the LMS dashboard.
2. Student uploads the completion file (PDF/Word/ZIP).
3. System checks that the submission date is before the deadline.
4. Plagiarism verification triggers automatically.
5. System returns confirmation ID and marks task status to 'Completed'.
        """,
        "user_stories": """
# User Stories & Acceptance Criteria

### US-ED-601: Student Lockdown Browser Exam
**As a** School Instructor  
**I want to** lock down copy/paste actions during online quizzes  
**So that** we maintain exam integrity and prevent cheating.

*Acceptance Criteria:*
- **AC1:** Quiz interface blocks keyboard clipboard commands (Ctrl+C, Ctrl+V).
- **AC2:** Leaving the window focus triggers warning alert to the supervisor dashboard.
- **AC3:** Test auto-submits on 3 focus-loss actions.

---

### US-ED-602: Real-time SMS Grade alerts
**As a** Registered Parent  
**I want to** receive instant notifications when my child's midterm score falls below passing criteria  
**So that** I can coordinate study support immediately.

*Acceptance Criteria:*
- **AC1:** System scans newly published grades against low-passing criteria.
- **AC2:** Alerts trigger SMS message within 5 minutes.
- **AC3:** Parent can disable grade triggers from settings page.
        """,
        "db_suggestions": """
# Database Design Suggestions

Suggested stack: **MariaDB or PostgreSQL** for relational student database management.

## Entity Relationship Outline
```mermaid
erDiagram
    COURSES ||--o{ ENROLLMENTS : registers
    STUDENTS ||--o{ ENROLLMENTS : attends
    COURSES ||--o{ ASSIGNMENTS : contains
```

## SQL DDL Scripts
Database schema mapping academic files:

```sql
-- Students SIS Registry
CREATE TABLE students (
    student_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    parent_email VARCHAR(100),
    enrolled_date DATE DEFAULT CURRENT_DATE
);

-- LMS Course Directory
CREATE TABLE courses (
    course_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_code VARCHAR(10) UNIQUE NOT NULL,
    subject_title VARCHAR(100) NOT NULL,
    credits INT DEFAULT 3
);

-- Course Gradebook Database
CREATE TABLE gradebook (
    grade_id BIGSERIAL PRIMARY KEY,
    student_id UUID REFERENCES students(student_id),
    course_id UUID REFERENCES courses(course_id),
    assignment_weight NUMERIC(5, 2) NOT NULL,
    grade_score NUMERIC(5, 2) NOT NULL CHECK (grade_score BETWEEN 0 AND 100),
    graded_by_user_id UUID NOT NULL
);
```
        """
    },

    "Manufacturing & Production": {
        "features": ["Production Planning (MRP)", "Machine Downtime Tracker", "Quality Control (QC)", "Bill of Materials (BOM)", "Shift & Labor Scheduling", "Supplier & Raw Material Mgmt"],
        "default_scope": "Build a Manufacturing ERP covering production scheduling, machine telemetry, QC inspection workflows, Bill of Materials management, and supplier procurement integration.",
        "kpi_metrics": {"total_requirements": "30 Detailed Items", "avg_complexity": "High (M3-M5)", "compliance_grade": "ISO 9001 / ISO 14001 Ready"},
        "brd": """
# Business Requirements Document (BRD)
## 1. Project Overview & Context
This BRD defines manufacturing operations requirements for **{project_name}**. The system will handle production line orchestration, quality inspection, shift management, and raw material procurement.

### 1.1 Business Goals & Success Metrics
- **Reduce Downtime:** Achieve <2% unplanned machine downtime by integrating IoT-based predictive maintenance alerts.
- **Improve QC Pass Rate:** Target ≥98.5% first-pass quality yield across all production lines.
- **Streamline Procurement:** Automate re-order triggers when raw material stock falls below buffer thresholds.

### 1.2 Target Stakeholders
- **Plant Manager:** Monitors OEE (Overall Equipment Effectiveness), manages shift rosters.
- **Quality Inspector:** Records defect logs, signs off inspection checklists.
- **Procurement Officer:** Manages supplier POs and raw material inventory.

## 2. Core Workflow
```mermaid
graph TD
    A[Production Order Created] --> B[MRP Generates BOM & Work Orders]
    B --> C[Raw Materials Reserved from Inventory]
    C --> D[Production Line Execution]
    D --> E{{QC Inspection}}
    E -- Pass --> F[Finished Goods Warehouse]
    E -- Fail --> G[Rework or Scrap Log]
```

## 3. Scope of Requirements
- **MRP Engine:** Plan material requirements from sales orders.
- **Machine Telemetry:** IoT sensor feeds for predictive maintenance.
- **QC Inspection Module:** Digital checklists and defect tracking.

### 3.1 Custom Scope Context
*{scope_details}*
        """,
        "srs": """
# Software Requirements Specification (SRS)
## 1. Functional Requirements

### 1.1 Production Planning
- **Req-MP-1.1.1 (MRP Run):** The system must calculate material requirements nightly from open sales orders and current stock levels.
- **Req-MP-1.1.2 (Work Order Generation):** Approved production plans must auto-generate work orders assigned to specific production cells.

### 1.2 Quality Control
- **Req-MP-1.2.1 (Digital Inspection):** QC inspectors must record defect codes using a digital checklist tied to each batch.
- **Req-MP-1.2.2 (Defect Escalation):** Batches with defect rate >2% must automatically escalate to the Quality Manager dashboard.

## 2. Non-Functional Requirements
### 2.1 Reliability
- **99.5% uptime** for production scheduling APIs during shift hours.
- **ISO 9001 audit trail** — all QC events must be logged with operator ID, timestamp, and defect classification.
        """,
        "use_cases": """
# Use Case Specifications

| Use Case ID | Use Case Name | Actor | Preconditions | Postconditions |
| :--- | :--- | :--- | :--- | :--- |
| **UC-MP-101** | Create Production Order | Plant Manager | Sales order approved | Work orders dispatched to production cells |
| **UC-MP-102** | Log QC Inspection Result | Quality Inspector | Batch production complete | Pass/Fail status recorded, defect log updated |
| **UC-MP-103** | Trigger Reorder Alert | Procurement System | Stock < reorder threshold | Purchase order auto-generated to supplier |

### Use Case Flow: UC-MP-101 (Create Production Order)
1. Plant Manager reviews approved sales orders in the system.
2. System runs MRP calculation to determine material shortages.
3. Production Order is created with target quantity and delivery date.
4. Work orders are auto-assigned to available production cells.
5. Raw materials are reserved in inventory management module.
        """,
        "user_stories": """
# User Stories & Acceptance Criteria

### US-MP-201: Predictive Maintenance Alert
**As a** Plant Engineer
**I want to** receive early alerts when machine vibration or temperature exceeds safe thresholds
**So that** I can schedule preventive maintenance before a breakdown occurs.

*Acceptance Criteria:*
- **AC1:** IoT sensor readings are ingested every 30 seconds.
- **AC2:** Alert triggers when any reading exceeds the defined threshold for 3 consecutive readings.
- **AC3:** Alert is pushed to the engineer's mobile dashboard within 60 seconds.

---

### US-MP-202: Digital QC Checklist
**As a** Quality Inspector
**I want to** complete a digital inspection form on my tablet at the production line
**So that** QC records are stored instantly without paper-based lag.

*Acceptance Criteria:*
- **AC1:** Checklist is pre-loaded based on the product type and batch number.
- **AC2:** Inspector can flag defects with photo attachment.
- **AC3:** Completed form syncs to the central QC database within 10 seconds.
        """,
        "db_suggestions": """
# Database Design Suggestions

Suggested stack: **PostgreSQL** for relational manufacturing records; **TimescaleDB** extension for IoT time-series telemetry.

## Entity Relationship Outline
```mermaid
erDiagram
    PRODUCTION_ORDERS ||--o{ WORK_ORDERS : spawns
    WORK_ORDERS ||--o{ QC_INSPECTIONS : inspected_by
    MATERIALS ||--o{ PRODUCTION_ORDERS : consumed_in
```

## SQL DDL Scripts
```sql
CREATE TABLE production_orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_code VARCHAR(50) NOT NULL,
    target_quantity INT NOT NULL,
    planned_start DATE NOT NULL,
    planned_end DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'open'
);

CREATE TABLE qc_inspections (
    inspection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    work_order_id UUID REFERENCES production_orders(order_id),
    inspector_id VARCHAR(50) NOT NULL,
    defect_count INT DEFAULT 0,
    result VARCHAR(10) NOT NULL,  -- 'pass' / 'fail'
    inspected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```
        """
    },
    "Retail & POS": {
        "features": ["Point of Sale (POS) Terminal", "Loyalty & Rewards Program", "Multi-Store Inventory", "Customer CRM", "Pricing & Promotions Engine", "Sales Analytics Dashboard"],
        "default_scope": "Build a Retail ERP with a POS terminal integration, customer loyalty tracking, multi-store inventory management, and promotional pricing rules engine.",
        "kpi_metrics": {"total_requirements": "27 Detailed Items", "avg_complexity": "Medium (M2-M4)", "compliance_grade": "PCI-DSS / GDPR Ready"},
        "brd": """
# Business Requirements Document (BRD)
## 1. Project Overview & Context
This BRD outlines the retail management requirements for **{project_name}**. The platform integrates POS terminals, CRM data, loyalty rewards, and inventory synchronization across multiple store locations.

### 1.1 Business Goals
- **Accelerate Checkout Speed:** Reduce average transaction time at POS to under 45 seconds.
- **Boost Customer Retention:** Increase repeat purchases through personalized loyalty rewards.
- **Unify Multi-Store Inventory:** Synchronize stock levels across all branches in real time.

### 1.2 Target Stakeholders
- **Store Cashier:** Processes transactions, applies discounts, manages returns.
- **Store Manager:** Monitors sales targets, manages shift operations.
- **Marketing Manager:** Configures promotions, tracks loyalty redemption rates.

## 2. Core Workflow
```mermaid
graph TD
    A[Customer Arrives at POS] --> B[Scan Items & Apply Loyalty Card]
    B --> C{{Promo Code Check}}
    C -- Eligible --> D[Apply Discount]
    C -- Not Eligible --> E[Full Price Checkout]
    D --> F[Process Payment]
    E --> F
    F --> G[Update Inventory & Award Loyalty Points]
```

## 3. Scope of Requirements
- **POS Terminal:** Barcode scanning, payment processing, receipt printing.
- **Loyalty Engine:** Points accumulation, tier management, redemption rules.
- **Inventory Sync:** Real-time stock deduction across all store locations.

### 3.1 Custom Scope Context
*{scope_details}*
        """,
        "srs": """
# Software Requirements Specification (SRS)
## 1. Functional Requirements

### 1.1 POS Terminal
- **Req-RT-1.1.1 (Barcode Scan):** POS must process barcode/QR scans and retrieve product pricing within 200ms.
- **Req-RT-1.1.2 (Offline Mode):** POS terminals must cache up to 500 product SKUs locally and queue transactions when network is unavailable.

### 1.2 Loyalty Program
- **Req-RT-1.2.1 (Points Accrual):** 1 loyalty point is awarded for every $1 spent, rounded down.
- **Req-RT-1.2.2 (Tier Upgrade):** Customer tier is recalculated monthly based on trailing 90-day spend.

## 2. Non-Functional Requirements
### 2.1 Security
- All POS payment data must be tokenized — no raw card numbers stored.
- PCI-DSS Level 1 compliance required for payment processing modules.
        """,
        "use_cases": """
# Use Case Specifications

| Use Case ID | Use Case Name | Actor | Preconditions | Postconditions |
| :--- | :--- | :--- | :--- | :--- |
| **UC-RT-101** | Process POS Sale | Cashier | Items scanned, payment method selected | Receipt generated, inventory updated, points awarded |
| **UC-RT-102** | Redeem Loyalty Points | Customer | Sufficient points balance | Discount applied, points deducted |
| **UC-RT-103** | Run End-of-Day Report | Store Manager | Business day closed | Daily sales summary report generated |

### Use Case Flow: UC-RT-101 (Process POS Sale)
1. Cashier scans each product barcode at the POS terminal.
2. System retrieves product price and checks active promotions.
3. Customer presents loyalty card — system retrieves points balance.
4. Payment is processed via card/cash/QR.
5. Receipt is printed, inventory decremented, loyalty points awarded.
        """,
        "user_stories": """
# User Stories & Acceptance Criteria

### US-RT-201: Offline POS Resilience
**As a** Store Cashier
**I want to** continue processing sales when the internet is down
**So that** checkout operations don't halt during network outages.

*Acceptance Criteria:*
- **AC1:** POS loads product catalog from local cache within 3 seconds of startup.
- **AC2:** Offline transactions are queued and synced automatically when connectivity resumes.
- **AC3:** System alerts cashier with a banner when operating in offline mode.

---

### US-RT-202: Targeted Loyalty Promotion
**As a** Marketing Manager
**I want to** send personalized bonus point offers to high-value customers
**So that** I can increase purchase frequency among our top 20% spenders.

*Acceptance Criteria:*
- **AC1:** System identifies top 20% customers by trailing 90-day spend.
- **AC2:** Bonus offer is delivered via SMS and in-app notification.
- **AC3:** Offer tracks redemption rate and expires automatically after 14 days.
        """,
        "db_suggestions": """
# Database Design Suggestions

Suggested stack: **MySQL / PostgreSQL** for transactional retail data; **Redis** for real-time inventory cache at POS.

## Entity Relationship Outline
```mermaid
erDiagram
    CUSTOMERS ||--o{ TRANSACTIONS : makes
    TRANSACTIONS ||--o{ TRANSACTION_ITEMS : contains
    PRODUCTS ||--o{ TRANSACTION_ITEMS : included_in
    CUSTOMERS ||--|| LOYALTY_ACCOUNTS : has
```

## SQL DDL Scripts
```sql
CREATE TABLE customers (
    customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(20),
    loyalty_tier VARCHAR(20) DEFAULT 'Bronze',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(customer_id),
    store_id INT NOT NULL,
    total_amount NUMERIC(10,2) NOT NULL,
    points_earned INT DEFAULT 0,
    payment_method VARCHAR(20),
    transacted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
        """
    },
    "Banking & Insurance": {
        "features": ["Core Banking Ledger", "Loan Origination System", "Policy Management", "Claims Processing", "KYC / AML Compliance", "Risk Scoring Engine"],
        "default_scope": "Design a Banking & Insurance platform covering core ledger management, loan origination workflows, policy lifecycle management, and automated claims adjudication.",
        "kpi_metrics": {"total_requirements": "36 Detailed Items", "avg_complexity": "Very High (M4-M6)", "compliance_grade": "Basel III / IFRS 17 / AML Ready"},
        "brd": """
# Business Requirements Document (BRD)
## 1. Project Overview & Context
This BRD defines core requirements for **{project_name}**, a banking and insurance management platform. It covers core banking, loan products, insurance policy lifecycle, claims, and regulatory compliance modules.

### 1.1 Business Goals
- **Accelerate Loan Decisions:** Reduce loan origination time from 5 days to under 24 hours via automated credit scoring.
- **Streamline Claims:** Achieve 80% of simple claims adjudicated within 48 hours without manual review.
- **Ensure Regulatory Compliance:** Maintain full AML/KYC logs and Basel III capital adequacy reporting.

### 1.2 Target Stakeholders
- **Loan Officer:** Reviews applications, triggers credit checks, issues approval letters.
- **Claims Adjudicator:** Reviews filed claims, requests documentation, approves payouts.
- **Compliance Officer:** Monitors transaction flags, files SAR reports.

## 2. Core Workflow
```mermaid
graph TD
    A[Loan Application Submitted] --> B[KYC & AML Verification]
    B --> C[Automated Credit Scoring]
    C -- Score >= 650 --> D[Conditional Approval]
    C -- Score < 650 --> E[Manual Review Queue]
    D --> F[Loan Agreement Signed]
    F --> G[Funds Disbursed]
```

## 3. Scope of Requirements
- **Core Banking:** Account management, interest calculation, transaction ledger.
- **Loan Origination:** Application intake, document verification, disbursement.
- **Claims Processing:** First Notice of Loss (FNOL), adjudication, payout.

### 3.1 Custom Scope Context
*{scope_details}*
        """,
        "srs": """
# Software Requirements Specification (SRS)
## 1. Functional Requirements

### 1.1 Loan Origination
- **Req-BI-1.1.1 (Auto Credit Score):** System must query credit bureau APIs and calculate a proprietary composite score within 30 seconds.
- **Req-BI-1.1.2 (Document Verification):** Identity documents must be verified via OCR + facial recognition before approval proceeds.

### 1.2 Claims Processing
- **Req-BI-1.2.1 (FNOL Capture):** Claimant can submit FNOL via web portal or mobile app with photo attachments.
- **Req-BI-1.2.2 (Auto Adjudication):** Claims under $500 with matching policy coverage must be auto-approved without manual review.

## 2. Non-Functional Requirements
### 2.1 Regulatory Compliance
- All customer PII must be encrypted at rest (AES-256) and in transit (TLS 1.3).
- Full audit trail for every ledger entry to satisfy Basel III requirements.
        """,
        "use_cases": """
# Use Case Specifications

| Use Case ID | Use Case Name | Actor | Preconditions | Postconditions |
| :--- | :--- | :--- | :--- | :--- |
| **UC-BI-101** | Submit Loan Application | Applicant | Account created, KYC verified | Application ID issued, credit check triggered |
| **UC-BI-102** | Adjudicate Insurance Claim | Claims Adjudicator | FNOL filed, documents uploaded | Claim approved/rejected, payout initiated |
| **UC-BI-103** | Flag AML Suspicious Transaction | AML Engine | Transaction above reporting threshold | SAR report queued for Compliance Officer |

### Use Case Flow: UC-BI-101 (Submit Loan Application)
1. Applicant completes loan application form specifying amount, term, and purpose.
2. System triggers KYC verification against government ID database.
3. Credit bureau API is queried — composite score calculated.
4. If score ≥ threshold, conditional approval letter is generated.
5. Applicant signs digital agreement; disbursement is scheduled.
        """,
        "user_stories": """
# User Stories & Acceptance Criteria

### US-BI-201: Automated Credit Decision
**As a** Loan Applicant
**I want to** receive a preliminary loan decision within minutes of submitting my application
**So that** I don't have to wait days to plan my finances.

*Acceptance Criteria:*
- **AC1:** Credit score returned from bureau API within 30 seconds.
- **AC2:** Decision email sent within 5 minutes of application submission.
- **AC3:** If manual review required, applicant is notified with expected turnaround time.

---

### US-BI-202: Instant Small Claims Settlement
**As a** Policyholder
**I want to** receive an instant payout for minor claims under $500
**So that** I don't have to follow up multiple times for small reimbursements.

*Acceptance Criteria:*
- **AC1:** Claim amount and policy coverage are cross-checked automatically.
- **AC2:** Auto-approved claims trigger bank transfer within 24 hours.
- **AC3:** Claimant receives SMS and email confirmation upon approval.
        """,
        "db_suggestions": """
# Database Design Suggestions

Suggested stack: **Oracle DB / PostgreSQL** for ACID-compliant banking ledgers; **Apache Kafka** for real-time AML event streaming.

## Entity Relationship Outline
```mermaid
erDiagram
    CUSTOMERS ||--o{ ACCOUNTS : owns
    ACCOUNTS ||--o{ LEDGER_ENTRIES : records
    CUSTOMERS ||--o{ LOAN_APPLICATIONS : submits
    CUSTOMERS ||--o{ POLICIES : holds
    POLICIES ||--o{ CLAIMS : generates
```

## SQL DDL Scripts
```sql
CREATE TABLE loan_applications (
    application_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL,
    loan_amount NUMERIC(14,2) NOT NULL,
    term_months INT NOT NULL,
    credit_score INT,
    status VARCHAR(20) DEFAULT 'pending',
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE claims (
    claim_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID NOT NULL,
    claim_amount NUMERIC(12,2) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'submitted',
    adjudicated_at TIMESTAMP
);
```
        """
    },
    "HR & Payroll": {
        "features": ["Employee Records (HRIS)", "Payroll Processing Engine", "Leave & Attendance Management", "Performance Review Cycles", "Recruitment & Onboarding", "Benefits & Compensation"],
        "default_scope": "Design an HR & Payroll ERP managing the full employee lifecycle — from recruitment and onboarding through payroll calculation, leave tracking, and performance management.",
        "kpi_metrics": {"total_requirements": "29 Detailed Items", "avg_complexity": "Medium (M2-M4)", "compliance_grade": "GDPR / FLSA / Labor Law Ready"},
        "brd": """
# Business Requirements Document (BRD)
## 1. Project Overview & Context
This BRD defines requirements for **{project_name}**, covering the full employee lifecycle — recruitment, payroll, leave management, and performance reviews.

### 1.1 Business Goals
- **Payroll Accuracy:** Achieve 100% payroll accuracy with automated tax and benefits deductions.
- **Reduce Admin Overhead:** Cut HR administrative hours by 60% through self-service employee portals.
- **Talent Retention:** Implement structured performance cycles to identify and retain top performers.

### 1.2 Target Stakeholders
- **HR Manager:** Manages employee records, approves leave requests, oversees recruitment.
- **Payroll Specialist:** Runs monthly payroll, handles deductions and tax filings.
- **Employee:** Views payslips, applies for leave, completes performance reviews.

## 2. Core Workflow
```mermaid
graph TD
    A[Employee Submits Leave Request] --> B[Manager Notified]
    B --> C{{Approve / Reject}}
    C -- Approved --> D[Leave Calendar Updated]
    C -- Rejected --> E[Employee Notified with Reason]
    D --> F[Payroll Adjusted for Leave Type]
```

## 3. Scope
- **HRIS:** Centralized employee records, org chart, contract management.
- **Payroll:** Salary calculation, tax deductions, payslip generation.
- **Leave Management:** Leave types, balance tracking, approval workflows.

### 3.1 Custom Scope Context
*{scope_details}*
        """,
        "srs": """
# Software Requirements Specification (SRS)
## 1. Functional Requirements

### 1.1 Payroll Processing
- **Req-HR-1.1.1 (Gross Pay):** System must calculate gross pay based on salary grade, overtime hours, and active allowances.
- **Req-HR-1.1.2 (Tax Deductions):** System must apply statutory tax deductions per jurisdiction and generate tax certificates annually.

### 1.2 Leave Management
- **Req-HR-1.2.1 (Leave Balance):** Employee leave balances must auto-refresh on the 1st of each month.
- **Req-HR-1.2.2 (Approval SLA):** Manager must approve or reject leave requests within 48 hours; system escalates after that.

## 2. Non-Functional Requirements
### 2.1 Privacy
- Employee PII must be stored in GDPR-compliant encrypted fields.
- Payroll data must only be accessible to authorized HR and Finance roles.
        """,
        "use_cases": """
# Use Case Specifications

| Use Case ID | Use Case Name | Actor | Preconditions | Postconditions |
| :--- | :--- | :--- | :--- | :--- |
| **UC-HR-101** | Process Monthly Payroll | Payroll Specialist | Attendance data finalized | Payslips generated, bank transfers initiated |
| **UC-HR-102** | Submit Leave Request | Employee | Sufficient leave balance | Request sent to manager for approval |
| **UC-HR-103** | Conduct Performance Review | HR Manager | Review cycle opened | Review scores recorded, development plans created |

### Use Case Flow: UC-HR-101 (Process Monthly Payroll)
1. Payroll specialist locks attendance data for the month.
2. System calculates gross pay for all active employees.
3. Statutory deductions (tax, pension, insurance) are applied.
4. Net pay is calculated and payslips are generated as PDFs.
5. Bank transfer file is exported and submitted to finance.
        """,
        "user_stories": """
# User Stories & Acceptance Criteria

### US-HR-201: Self-Service Payslip Access
**As an** Employee
**I want to** download my payslip for any month through the HR portal
**So that** I don't need to contact HR for pay documentation.

*Acceptance Criteria:*
- **AC1:** Payslips are published within 2 business days of payroll run.
- **AC2:** Employee can download payslip as a password-protected PDF.
- **AC3:** Payslip history is retained for at least 5 years.

---

### US-HR-202: Automated Leave Escalation
**As an** HR Manager
**I want to** ensure no leave request sits unanswered for more than 48 hours
**So that** employees receive timely responses for planning purposes.

*Acceptance Criteria:*
- **AC1:** System sends manager a reminder after 24 hours of no action.
- **AC2:** After 48 hours, request escalates to the HR Manager.
- **AC3:** Employee is notified of escalation automatically.
        """,
        "db_suggestions": """
# Database Design Suggestions

Suggested stack: **PostgreSQL** with row-level security for payroll privacy; **Elasticsearch** for employee search and org chart queries.

## Entity Relationship Outline
```mermaid
erDiagram
    EMPLOYEES ||--|| POSITIONS : holds
    EMPLOYEES ||--o{ PAYROLL_RECORDS : paid_via
    EMPLOYEES ||--o{ LEAVE_REQUESTS : submits
```

## SQL DDL Scripts
```sql
CREATE TABLE employees (
    employee_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    department VARCHAR(80),
    salary_grade VARCHAR(10),
    employment_type VARCHAR(20) DEFAULT 'full-time',
    hired_date DATE NOT NULL
);

CREATE TABLE payroll_records (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id UUID REFERENCES employees(employee_id),
    pay_period DATE NOT NULL,
    gross_pay NUMERIC(12,2) NOT NULL,
    deductions NUMERIC(12,2) DEFAULT 0,
    net_pay NUMERIC(12,2) NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
        """
    },
    "Logistics & Transportation": {
        "features": ["Fleet Management & GPS Tracking", "Route Optimization Engine", "Freight & Cargo Booking", "Driver Scheduling", "Customs & Compliance Docs", "Delivery Proof (ePOD)"],
        "default_scope": "Build a Logistics & Transportation ERP with real-time fleet GPS tracking, route optimization, freight booking management, driver scheduling, and customs documentation workflows.",
        "kpi_metrics": {"total_requirements": "28 Detailed Items", "avg_complexity": "High (M3-M5)", "compliance_grade": "DOT / FMCSA / Customs Ready"},
        "brd": """
# Business Requirements Document (BRD)
## 1. Project Overview & Context
This BRD defines requirements for **{project_name}**, a logistics and transportation management platform handling fleet tracking, freight booking, route planning, and last-mile delivery proof.

### 1.1 Business Goals
- **Optimize Routes:** Reduce average fuel cost per delivery by 18% through AI-powered route optimization.
- **Improve On-Time Delivery:** Achieve ≥97% on-time delivery rate across all routes.
- **Paperless Operations:** Eliminate manual delivery paperwork with electronic proof of delivery (ePOD).

### 1.2 Target Stakeholders
- **Fleet Dispatcher:** Assigns drivers, monitors vehicle locations, handles route deviations.
- **Driver:** Receives job assignments, captures delivery photos and signatures.
- **Operations Manager:** Reviews KPIs, fuel costs, and SLA compliance metrics.

## 2. Core Workflow
```mermaid
graph TD
    A[Freight Order Received] --> B[Route Optimization Engine]
    B --> C[Driver & Vehicle Assigned]
    C --> D[Real-time GPS Tracking Active]
    D --> E[Driver Arrives at Delivery Point]
    E --> F[ePOD Captured — Photo + Signature]
    F --> G[Delivery Confirmed in System]
```

## 3. Scope
- **Fleet Tracking:** Live GPS coordinates updated every 60 seconds.
- **Route Planning:** Multi-stop optimization considering traffic, weight limits, and delivery windows.
- **ePOD:** Digital signature and photo capture at delivery point.

### 3.1 Custom Scope Context
*{scope_details}*
        """,
        "srs": """
# Software Requirements Specification (SRS)
## 1. Functional Requirements

### 1.1 Fleet Tracking
- **Req-LT-1.1.1 (GPS Refresh):** Vehicle GPS coordinates must be ingested and stored every 60 seconds during active trips.
- **Req-LT-1.1.2 (Geofence Alerts):** System must trigger alerts when a vehicle deviates more than 500m from the assigned route.

### 1.2 Proof of Delivery
- **Req-LT-1.2.1 (ePOD Capture):** Driver mobile app must capture recipient signature and at least one delivery photo.
- **Req-LT-1.2.2 (Sync):** ePOD data must sync to the server within 30 seconds of capture on LTE or WiFi.

## 2. Non-Functional Requirements
### 2.1 Performance
- Map rendering with up to 500 simultaneous vehicle markers must load within 3 seconds.
- Route optimization for up to 50 stops must complete in under 10 seconds.
        """,
        "use_cases": """
# Use Case Specifications

| Use Case ID | Use Case Name | Actor | Preconditions | Postconditions |
| :--- | :--- | :--- | :--- | :--- |
| **UC-LT-101** | Assign Driver to Delivery Route | Fleet Dispatcher | Freight order confirmed | Driver notified, route loaded on mobile app |
| **UC-LT-102** | Capture Electronic Proof of Delivery | Driver | Arrival at delivery address | ePOD synced, order status updated to 'Delivered' |
| **UC-LT-103** | Generate Route Deviation Alert | System | Vehicle exceeds geofence boundary | Alert sent to dispatcher, driver notified |

### Use Case Flow: UC-LT-101 (Assign Driver to Delivery Route)
1. Dispatcher views open freight orders in the dispatch dashboard.
2. System suggests optimal driver/vehicle match based on proximity and capacity.
3. Dispatcher confirms assignment — driver receives push notification.
4. Route is displayed on driver's mobile app with turn-by-turn navigation.
5. GPS tracking activates and fleet map updates in real time.
        """,
        "user_stories": """
# User Stories & Acceptance Criteria

### US-LT-201: Live Fleet Map
**As a** Fleet Dispatcher
**I want to** see all active vehicles on a live map dashboard
**So that** I can quickly redirect drivers during unexpected delays.

*Acceptance Criteria:*
- **AC1:** Map refreshes vehicle positions every 60 seconds.
- **AC2:** Each vehicle marker shows driver name, current speed, and ETA.
- **AC3:** Clicking a vehicle opens the full trip details panel.

---

### US-LT-202: Digital Proof of Delivery
**As a** Operations Manager
**I want to** access ePOD records with photo evidence for every completed delivery
**So that** I can resolve customer disputes with documented proof.

*Acceptance Criteria:*
- **AC1:** Each delivery record links to its ePOD with photo and signature.
- **AC2:** ePOD is accessible from the order detail page within 5 minutes of capture.
- **AC3:** Records are retained for a minimum of 3 years.
        """,
        "db_suggestions": """
# Database Design Suggestions

Suggested stack: **PostgreSQL + PostGIS** for geospatial fleet data; **TimescaleDB** for GPS time-series telemetry.

## Entity Relationship Outline
```mermaid
erDiagram
    VEHICLES ||--o{ TRIPS : assigned_to
    DRIVERS ||--o{ TRIPS : operates
    TRIPS ||--o{ DELIVERY_STOPS : includes
    DELIVERY_STOPS ||--o{ EPOD_RECORDS : captures
```

## SQL DDL Scripts
```sql
CREATE TABLE trips (
    trip_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL,
    driver_id UUID NOT NULL,
    planned_start TIMESTAMP NOT NULL,
    actual_start TIMESTAMP,
    status VARCHAR(20) DEFAULT 'scheduled'
);

CREATE TABLE epod_records (
    epod_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stop_id UUID NOT NULL,
    photo_url TEXT,
    signature_url TEXT,
    recipient_name VARCHAR(100),
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
        """
    },
    "Agriculture & FarmTech": {
        "features": ["Crop Planning & Rotation", "IoT Soil & Weather Sensors", "Irrigation Automation", "Livestock Management", "Harvest & Yield Tracking", "Farm-to-Market Supply"],
        "default_scope": "Build an Agriculture ERP integrating IoT sensors for soil/weather monitoring, crop planning, automated irrigation control, livestock tracking, and yield reporting with supply chain traceability.",
        "kpi_metrics": {"total_requirements": "24 Detailed Items", "avg_complexity": "Medium (M2-M4)", "compliance_grade": "GAP / Organic Certification Ready"},
        "brd": """
# Business Requirements Document (BRD)
## 1. Project Overview & Context
This BRD defines requirements for **{project_name}**, an agricultural management platform covering crop planning, IoT-driven irrigation, livestock health monitoring, and farm-to-market traceability.

### 1.1 Business Goals
- **Increase Crop Yield:** Boost average yield per hectare by 15% through precision irrigation and soil analytics.
- **Reduce Water Waste:** Cut irrigation water usage by 30% with automated soil moisture-based scheduling.
- **Full Traceability:** Track produce from field to consumer, satisfying GAP certification requirements.

### 1.2 Target Stakeholders
- **Farm Manager:** Monitors crop health, plans planting schedules, reviews yield reports.
- **Agronomist:** Analyzes soil data, recommends fertilizer and irrigation adjustments.
- **Logistics Coordinator:** Manages harvest-to-distribution handoffs.

## 2. Core Workflow
```mermaid
graph TD
    A[Soil Moisture Sensor Reading] --> B{{Below Threshold?}}
    B -- Yes --> C[Trigger Automated Irrigation]
    B -- No --> D[Schedule Next Reading in 1 Hour]
    C --> E[Log Irrigation Event]
    E --> F[Agronomist Dashboard Updated]
```

## 3. Scope
- **IoT Integration:** Soil, weather, and moisture sensor data ingestion.
- **Irrigation Control:** Automated zone-based watering schedules.
- **Traceability:** Batch and lot numbering from seed to sale.

### 3.1 Custom Scope Context
*{scope_details}*
        """,
        "srs": """
# Software Requirements Specification (SRS)
## 1. Functional Requirements

### 1.1 IoT Sensor Integration
- **Req-AG-1.1.1 (Sensor Ingest):** System must receive and store sensor readings from up to 1,000 IoT devices every 15 minutes.
- **Req-AG-1.1.2 (Alert Threshold):** Soil moisture dropping below 35% field capacity must trigger an irrigation alert within 5 minutes.

### 1.2 Crop Traceability
- **Req-AG-1.2.1 (Batch Tracking):** Every crop batch must be assigned a unique QR-coded lot number traceable from planting to delivery.
- **Req-AG-1.2.2 (Audit Logs):** All chemical applications (pesticides, fertilizers) must be logged with date, quantity, and applicator.

## 2. Non-Functional Requirements
### 2.1 Availability
- The irrigation control API must maintain 99.9% uptime during growing season.
- System must operate in low-connectivity rural areas with offline sync capability.
        """,
        "use_cases": """
# Use Case Specifications

| Use Case ID | Use Case Name | Actor | Preconditions | Postconditions |
| :--- | :--- | :--- | :--- | :--- |
| **UC-AG-101** | Trigger Automated Irrigation | IoT System | Soil moisture < threshold | Irrigation zone activated, event logged |
| **UC-AG-102** | Record Harvest Yield | Farm Manager | Harvest complete | Yield data logged, lot number assigned |
| **UC-AG-103** | Generate Traceability Report | Logistics Coordinator | Produce batch dispatched | QR-linked trace report available for buyers |

### Use Case Flow: UC-AG-101 (Trigger Automated Irrigation)
1. Soil moisture sensor transmits reading below 35% field capacity.
2. System evaluates active irrigation schedule and weather forecast.
3. If no rain expected within 6 hours, irrigation command is sent.
4. Irrigation zone valve opens and duration is calculated based on crop type.
5. Irrigation event is logged with zone ID, duration, and water volume.
        """,
        "user_stories": """
# User Stories & Acceptance Criteria

### US-AG-201: Smart Irrigation Dashboard
**As a** Farm Manager
**I want to** see all irrigation zones and their soil moisture levels on a single dashboard
**So that** I can make informed watering decisions without walking the field.

*Acceptance Criteria:*
- **AC1:** Dashboard displays real-time moisture levels for all registered sensor zones.
- **AC2:** Zones below threshold are highlighted in amber/red.
- **AC3:** Manager can manually trigger or pause irrigation from the dashboard.

---

### US-AG-202: Harvest Traceability QR Code
**As a** Logistics Coordinator
**I want to** print a QR code for every harvest batch
**So that** buyers and inspectors can trace the produce back to the field and treatment records.

*Acceptance Criteria:*
- **AC1:** QR code links to a public traceability page with field ID, planting date, and treatments applied.
- **AC2:** QR code is generated within 60 seconds of harvest record submission.
- **AC3:** Page is mobile-friendly and accessible without login.
        """,
        "db_suggestions": """
# Database Design Suggestions

Suggested stack: **PostgreSQL + TimescaleDB** for IoT sensor time-series; **MinIO / S3** for traceability report and image storage.

## Entity Relationship Outline
```mermaid
erDiagram
    FIELDS ||--o{ CROP_BATCHES : grows
    FIELDS ||--o{ SENSOR_READINGS : monitored_by
    CROP_BATCHES ||--o{ TREATMENT_LOGS : receives
    CROP_BATCHES ||--o{ HARVESTS : produces
```

## SQL DDL Scripts
```sql
CREATE TABLE fields (
    field_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    field_name VARCHAR(100) NOT NULL,
    area_hectares NUMERIC(8,2),
    soil_type VARCHAR(50),
    location_coords POINT
);

CREATE TABLE sensor_readings (
    reading_id BIGSERIAL PRIMARY KEY,
    field_id UUID REFERENCES fields(field_id),
    sensor_type VARCHAR(30) NOT NULL,  -- 'moisture', 'temperature', 'ph'
    value NUMERIC(8,3) NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```
        """
    },
    "Real Estate & PropTech": {
        "features": ["Property Listings Management", "Tenant CRM & Leasing", "Maintenance Request Tracking", "Rent Collection & Invoicing", "Document & Contract Vault", "Analytics & Valuation Reports"],
        "default_scope": "Build a Real Estate ERP managing property listings, tenant CRM, lease lifecycle management, maintenance ticketing, automated rent invoicing, and market valuation analytics.",
        "kpi_metrics": {"total_requirements": "25 Detailed Items", "avg_complexity": "Medium (M2-M4)", "compliance_grade": "Fair Housing / GDPR / RERA Ready"},
        "brd": """
# Business Requirements Document (BRD)
## 1. Project Overview & Context
This BRD outlines the property management requirements for **{project_name}**, covering listings, tenant management, lease administration, maintenance workflows, and financial reporting.

### 1.1 Business Goals
- **Reduce Vacancy Rates:** Cut average vacancy duration by 40% through automated tenant matching and fast listing publication.
- **Automate Rent Collection:** Achieve 95% on-time rent collection with automated invoicing and payment reminders.
- **Streamline Maintenance:** Resolve 85% of tenant maintenance tickets within 72 hours.

### 1.2 Target Stakeholders
- **Property Manager:** Manages listings, approves leases, oversees maintenance.
- **Tenant:** Pays rent online, submits maintenance requests, accesses documents.
- **Finance Officer:** Tracks rental income, overdue accounts, and financial reports.

## 2. Core Workflow
```mermaid
graph TD
    A[Tenant Submits Maintenance Request] --> B[Property Manager Notified]
    B --> C[Assign to Maintenance Vendor]
    C --> D[Vendor Completes Work]
    D --> E[Tenant Confirms Resolution]
    E --> F[Ticket Closed & Invoice Logged]
```

## 3. Scope
- **Listings:** Property catalog with photos, specs, and availability status.
- **Leasing:** Digital lease signing, renewal reminders, termination workflows.
- **Maintenance:** Ticketing system with vendor assignment and SLA tracking.

### 3.1 Custom Scope Context
*{scope_details}*
        """,
        "srs": """
# Software Requirements Specification (SRS)
## 1. Functional Requirements

### 1.1 Rent Collection
- **Req-RE-1.1.1 (Auto Invoice):** Rent invoices must auto-generate on the 25th of each month for the upcoming rental period.
- **Req-RE-1.1.2 (Payment Reminder):** SMS and email reminders must fire 5 days before and on the due date for unpaid invoices.

### 1.2 Lease Management
- **Req-RE-1.2.1 (Digital Signature):** Lease agreements must support legally binding e-signature workflows.
- **Req-RE-1.2.2 (Renewal Alerts):** System must notify Property Manager 60 days before lease expiry.

## 2. Non-Functional Requirements
### 2.1 Security & Compliance
- All tenant documents must be stored in encrypted cloud storage with access audit logs.
- Platform must comply with Fair Housing Act for listing display rules.
        """,
        "use_cases": """
# Use Case Specifications

| Use Case ID | Use Case Name | Actor | Preconditions | Postconditions |
| :--- | :--- | :--- | :--- | :--- |
| **UC-RE-101** | Publish Property Listing | Property Manager | Property details entered | Listing live on portal within 10 minutes |
| **UC-RE-102** | Submit Maintenance Request | Tenant | Logged into tenant portal | Ticket created, vendor notified |
| **UC-RE-103** | Process Rent Payment | Tenant | Invoice generated | Payment recorded, receipt emailed |

### Use Case Flow: UC-RE-103 (Process Rent Payment)
1. Tenant receives rent invoice via email/SMS.
2. Tenant clicks payment link and selects payment method (bank transfer/card).
3. Payment gateway processes transaction.
4. System records payment against invoice and updates ledger.
5. Receipt PDF is emailed to tenant; landlord receives payment confirmation.
        """,
        "user_stories": """
# User Stories & Acceptance Criteria

### US-RE-201: Automated Rent Reminder
**As a** Property Manager
**I want to** automatically send payment reminders to tenants with unpaid rent
**So that** I don't have to manually chase overdue payments.

*Acceptance Criteria:*
- **AC1:** System sends reminder 5 days before and on the due date.
- **AC2:** If still unpaid after due date, reminder escalates every 3 days.
- **AC3:** Manager receives a weekly overdue rent summary.

---

### US-RE-202: Maintenance SLA Dashboard
**As a** Property Manager
**I want to** see all open maintenance tickets with their SLA countdown
**So that** I can prioritize urgent issues and hold vendors accountable.

*Acceptance Criteria:*
- **AC1:** Dashboard displays all open tickets sorted by SLA urgency.
- **AC2:** Tickets past 72 hours are highlighted in red.
- **AC3:** Manager can re-assign a ticket to another vendor with one click.
        """,
        "db_suggestions": """
# Database Design Suggestions

Suggested stack: **PostgreSQL** for property and lease records; **AWS S3 / Azure Blob** for document and image vault.

## Entity Relationship Outline
```mermaid
erDiagram
    PROPERTIES ||--o{ UNITS : contains
    UNITS ||--o{ LEASES : leased_via
    LEASES ||--|| TENANTS : held_by
    UNITS ||--o{ MAINTENANCE_TICKETS : has
```

## SQL DDL Scripts
```sql
CREATE TABLE properties (
    property_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    address TEXT NOT NULL,
    total_units INT NOT NULL,
    property_type VARCHAR(50)
);

CREATE TABLE leases (
    lease_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    monthly_rent NUMERIC(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'active'
);
```
        """
    },
    "Legal & Compliance": {
        "features": ["Case & Matter Management", "Document Drafting & Versioning", "Compliance Calendar & Deadlines", "Client Billing & Time Tracking", "Court Filing Management", "Regulatory Change Monitoring"],
        "default_scope": "Design a Legal ERP covering case matter management, document versioning, compliance deadline calendars, client billing, time tracking, and court filing workflows.",
        "kpi_metrics": {"total_requirements": "26 Detailed Items", "avg_complexity": "High (M3-M5)", "compliance_grade": "GDPR / Bar Association Standards Ready"},
        "brd": """
# Business Requirements Document (BRD)
## 1. Project Overview & Context
This BRD defines requirements for **{project_name}**, a legal practice management platform covering case management, document drafting, compliance deadlines, client invoicing, and court submissions.

### 1.1 Business Goals
- **Reduce Missed Deadlines:** Eliminate court deadline misses through automated compliance calendar alerts.
- **Streamline Billing:** Automate client invoicing from time-tracked activities to reduce billing disputes.
- **Secure Document Management:** Provide version-controlled, encrypted document vault for all case files.

### 1.2 Target Stakeholders
- **Attorney:** Manages cases, drafts documents, tracks billable hours.
- **Paralegal:** Manages court filings, deadline calendars, and document requests.
- **Client:** Views case status, uploads documents, reviews invoices.

## 2. Core Workflow
```mermaid
graph TD
    A[New Case Opened] --> B[Client & Matter Created]
    B --> C[Key Deadlines Added to Compliance Calendar]
    C --> D[Attorney Tracks Billable Hours]
    D --> E[Monthly Invoice Auto-Generated]
    E --> F[Client Reviews & Pays Invoice]
```

## 3. Scope
- **Case Management:** Matter intake, status tracking, stakeholder mapping.
- **Document Vault:** Version control, e-signature, access logs.
- **Billing:** Time entry, invoice generation, payment reconciliation.

### 3.1 Custom Scope Context
*{scope_details}*
        """,
        "srs": """
# Software Requirements Specification (SRS)
## 1. Functional Requirements

### 1.1 Deadline Management
- **Req-LC-1.1.1 (Calendar Sync):** Compliance deadlines must sync to attorney Outlook/Google calendars via iCal feed.
- **Req-LC-1.1.2 (Alert Cascade):** Alerts must fire 30, 14, 7, and 1 day before each court deadline.

### 1.2 Time & Billing
- **Req-LC-1.2.1 (Time Entry):** Attorneys must log billable time in 6-minute increments (0.1 hour) per standard billing practice.
- **Req-LC-1.2.2 (Invoice Generation):** Monthly invoices must auto-compile all approved time entries and disbursements.

## 2. Non-Functional Requirements
### 2.1 Security
- All case documents must be encrypted at rest and accessible only to assigned matter team members.
- Complete audit trail of document access, edits, and downloads.
        """,
        "use_cases": """
# Use Case Specifications

| Use Case ID | Use Case Name | Actor | Preconditions | Postconditions |
| :--- | :--- | :--- | :--- | :--- |
| **UC-LC-101** | Open New Legal Matter | Attorney | Client onboarded | Matter ID created, team assigned, calendar seeded |
| **UC-LC-102** | File Court Document | Paralegal | Document finalized and signed | Filing confirmation stored, deadline updated |
| **UC-LC-103** | Generate Client Invoice | Billing System | Month-end triggered | Invoice PDF sent to client via email |

### Use Case Flow: UC-LC-101 (Open New Legal Matter)
1. Attorney creates new matter with case type, jurisdiction, and client reference.
2. System generates unique matter number and creates document folder.
3. Key statutory deadlines are auto-populated from the jurisdiction template.
4. Matter team members are assigned with role-based access.
5. Compliance calendar entries are synced to team members' calendars.
        """,
        "user_stories": """
# User Stories & Acceptance Criteria

### US-LC-201: Court Deadline Alert Cascade
**As an** Attorney
**I want to** receive escalating reminders as court deadlines approach
**So that** I never miss a filing deadline due to oversight.

*Acceptance Criteria:*
- **AC1:** Alerts fire at 30, 14, 7, and 1 day intervals via email and push notification.
- **AC2:** 1-day alert includes a direct link to the related document for immediate action.
- **AC3:** Attorney can snooze a reminder with a mandatory note explaining the delay.

---

### US-LC-202: Automated Monthly Invoice
**As a** Billing Administrator
**I want to** auto-generate client invoices at month-end from approved time entries
**So that** billing is consistent and reduces manual reconciliation effort.

*Acceptance Criteria:*
- **AC1:** Invoice compiles all approved time entries and disbursements for the billing period.
- **AC2:** Invoice PDF is generated and emailed to the client within 2 hours of month-end close.
- **AC3:** Invoice status updates automatically when payment is received.
        """,
        "db_suggestions": """
# Database Design Suggestions

Suggested stack: **PostgreSQL** with row-level security for matter isolation; **S3-compatible vault** for encrypted document storage.

## Entity Relationship Outline
```mermaid
erDiagram
    CLIENTS ||--o{ MATTERS : hires_for
    MATTERS ||--o{ TIME_ENTRIES : billed_via
    MATTERS ||--o{ DOCUMENTS : files
    MATTERS ||--o{ DEADLINES : has
```

## SQL DDL Scripts
```sql
CREATE TABLE matters (
    matter_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    matter_number VARCHAR(30) UNIQUE NOT NULL,
    client_id UUID NOT NULL,
    case_type VARCHAR(80) NOT NULL,
    jurisdiction VARCHAR(80),
    status VARCHAR(20) DEFAULT 'open',
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE time_entries (
    entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    matter_id UUID REFERENCES matters(matter_id),
    attorney_id UUID NOT NULL,
    hours NUMERIC(5,1) NOT NULL,
    description TEXT,
    rate NUMERIC(8,2) NOT NULL,
    entry_date DATE NOT NULL,
    approved BOOLEAN DEFAULT FALSE
);
```
        """
    },
    "Government & Public Sector": {
        "features": ["Citizen Services Portal", "Budget & Expenditure Management", "Grant Management", "Permit & License Issuance", "Public Asset Registry", "Procurement & Tendering"],
        "default_scope": "Build a Government ERP for citizen service delivery, budget tracking, grant management, e-permit issuance, public asset registry, and transparent procurement/tendering workflows.",
        "kpi_metrics": {"total_requirements": "31 Detailed Items", "avg_complexity": "High (M3-M5)", "compliance_grade": "FISMA / Open Gov / GDPR Ready"},
        "brd": """
# Business Requirements Document (BRD)
## 1. Project Overview & Context
This BRD defines requirements for **{project_name}**, a public sector ERP platform enabling citizen service delivery, budget controls, permit processing, and transparent procurement management.

### 1.1 Business Goals
- **Digitize Citizen Services:** Migrate 80% of in-person service applications to the online citizen portal within 12 months.
- **Budget Transparency:** Provide real-time expenditure dashboards accessible to authorized auditors and the public.
- **Accelerate Permit Processing:** Reduce average permit issuance time from 21 days to 5 business days.

### 1.2 Target Stakeholders
- **Citizen:** Applies for permits, tracks application status, pays government fees.
- **Department Head:** Manages departmental budgets, approves expenditures.
- **Procurement Officer:** Publishes tenders, evaluates bids, awards contracts.

## 2. Core Workflow
```mermaid
graph TD
    A[Citizen Submits Permit Application] --> B[Document Verification]
    B --> C[Assign to Reviewing Officer]
    C --> D{{Inspection Required?}}
    D -- Yes --> E[Schedule Field Inspection]
    D -- No --> F[Approve & Issue Permit]
    E --> F
    F --> G[Citizen Notified, Permit Downloaded]
```

## 3. Scope
- **Citizen Portal:** Online applications, status tracking, digital permit downloads.
- **Budget Module:** Departmental budget allocation, expenditure tracking, audit trails.
- **Procurement:** Tender publishing, bid evaluation, contract awards.

### 3.1 Custom Scope Context
*{scope_details}*
        """,
        "srs": """
# Software Requirements Specification (SRS)
## 1. Functional Requirements

### 1.1 Citizen Services
- **Req-GV-1.1.1 (Online Application):** Citizens must be able to submit permit applications with document attachments without requiring in-person visits.
- **Req-GV-1.1.2 (Status Tracking):** Citizens must receive email/SMS updates at each stage of application processing.

### 1.2 Budget Management
- **Req-GV-1.2.1 (Budget Alerts):** Departments approaching 90% of budget utilization must trigger automatic alerts to the Finance Director.
- **Req-GV-1.2.2 (Expenditure Audit):** All expenditure entries must carry a digital approval trail viewable by auditors.

## 2. Non-Functional Requirements
### 2.1 Security & Accessibility
- Platform must achieve WCAG 2.1 AA accessibility compliance for the citizen portal.
- All citizen PII must be stored on government-approved data centers with FISMA compliance.
        """,
        "use_cases": """
# Use Case Specifications

| Use Case ID | Use Case Name | Actor | Preconditions | Postconditions |
| :--- | :--- | :--- | :--- | :--- |
| **UC-GV-101** | Submit Building Permit Application | Citizen | Account registered | Application ID issued, documents queued for review |
| **UC-GV-102** | Approve Departmental Budget Request | Finance Director | Budget request submitted | Budget allocated, department notified |
| **UC-GV-103** | Publish Procurement Tender | Procurement Officer | Tender details finalized | Tender live on public portal, submission period open |

### Use Case Flow: UC-GV-101 (Submit Building Permit Application)
1. Citizen registers on the portal and selects 'Building Permit' service.
2. Application form is completed with project details and documents attached.
3. System validates document completeness and assigns a reference number.
4. Application is routed to the reviewing officer for the relevant district.
5. Citizen receives email confirmation with expected decision timeline.
        """,
        "user_stories": """
# User Stories & Acceptance Criteria

### US-GV-201: Real-Time Permit Status
**As a** Citizen
**I want to** track the status of my permit application online
**So that** I don't have to call the department repeatedly for updates.

*Acceptance Criteria:*
- **AC1:** Citizen can view current stage (Submitted → Under Review → Approved/Rejected).
- **AC2:** Status updates are pushed via SMS and email within 1 hour of each stage change.
- **AC3:** If rejected, reason is clearly stated with resubmission instructions.

---

### US-GV-202: Transparent Budget Dashboard
**As a** Public Auditor
**I want to** view departmental expenditure breakdowns in a public dashboard
**So that** government spending is transparent and accountable.

*Acceptance Criteria:*
- **AC1:** Dashboard displays budget vs. actual spend per department.
- **AC2:** Data is refreshed daily and available without login.
- **AC3:** Drill-down view shows individual expenditure line items.
        """,
        "db_suggestions": """
# Database Design Suggestions

Suggested stack: **PostgreSQL** on government-approved infrastructure (on-premise or GovCloud); **Elasticsearch** for permit search and audit log queries.

## Entity Relationship Outline
```mermaid
erDiagram
    CITIZENS ||--o{ APPLICATIONS : submits
    APPLICATIONS ||--o{ REVIEW_STAGES : passes_through
    DEPARTMENTS ||--o{ BUDGETS : allocated
    BUDGETS ||--o{ EXPENDITURES : spent_on
```

## SQL DDL Scripts
```sql
CREATE TABLE applications (
    app_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id UUID NOT NULL,
    service_type VARCHAR(80) NOT NULL,
    reference_number VARCHAR(30) UNIQUE NOT NULL,
    status VARCHAR(30) DEFAULT 'submitted',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE expenditures (
    exp_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    budget_id UUID NOT NULL,
    amount NUMERIC(14,2) NOT NULL,
    description TEXT,
    approved_by VARCHAR(100),
    incurred_at DATE NOT NULL
);
```
        """
    },
    "Hospitality & Tourism": {
        "features": ["Hotel Property Management (PMS)", "Booking & Reservation Engine", "Restaurant POS & Menu", "Guest CRM & Loyalty", "Housekeeping Management", "Revenue & Rate Management"],
        "default_scope": "Build a Hospitality ERP with a hotel property management system, online reservation engine, restaurant POS, guest CRM and loyalty programs, housekeeping workflows, and dynamic revenue management.",
        "kpi_metrics": {"total_requirements": "27 Detailed Items", "avg_complexity": "Medium (M2-M4)", "compliance_grade": "PCI-DSS / GDPR / Tourism Board Ready"},
        "brd": """
# Business Requirements Document (BRD)
## 1. Project Overview & Context
This BRD defines requirements for **{project_name}**, a hospitality management platform covering hotel reservations, room management, restaurant operations, guest loyalty, and dynamic pricing.

### 1.1 Business Goals
- **Increase Occupancy Rate:** Target ≥85% average room occupancy through dynamic rate optimization.
- **Enhance Guest Experience:** Achieve guest satisfaction score ≥4.5/5 via personalized loyalty programs.
- **Streamline Housekeeping:** Reduce room turnaround time from 45 minutes to under 30 minutes.

### 1.2 Target Stakeholders
- **Front Desk Agent:** Manages check-ins, check-outs, and room assignments.
- **Revenue Manager:** Sets dynamic pricing rules, monitors occupancy and RevPAR.
- **Guest:** Manages bookings, accesses loyalty rewards, views receipts.

## 2. Core Workflow
```mermaid
graph TD
    A[Guest Makes Reservation Online] --> B[PMS Allocates Room]
    B --> C[Pre-Arrival Welcome Email Sent]
    C --> D[Guest Checks In at Front Desk]
    D --> E[Room Key Issued]
    E --> F[Housekeeping Notified on Checkout]
    F --> G[Room Cleaned & Status Updated]
```

## 3. Scope
- **PMS:** Room inventory, reservation management, check-in/out workflows.
- **Revenue Management:** Dynamic pricing based on occupancy, season, and demand signals.
- **Guest CRM:** Preference profiles, loyalty tiers, targeted offers.

### 3.1 Custom Scope Context
*{scope_details}*
        """,
        "srs": """
# Software Requirements Specification (SRS)
## 1. Functional Requirements

### 1.1 Reservation Engine
- **Req-HT-1.1.1 (Real-Time Availability):** Room availability must reflect cancellations and new bookings within 5 seconds across all booking channels.
- **Req-HT-1.1.2 (Channel Manager):** System must sync availability to OTA channels (Booking.com, Expedia) via channel manager API.

### 1.2 Dynamic Pricing
- **Req-HT-1.2.1 (Rate Rules):** Revenue manager must be able to define rate rules based on occupancy %, lead time, and day-of-week.
- **Req-HT-1.2.2 (Competitor Rates):** System should surface competitor rate benchmarks to support pricing decisions.

## 2. Non-Functional Requirements
### 2.1 Reliability
- Reservation booking engine must maintain 99.95% uptime with <500ms response time.
- All payment data must be processed via PCI-DSS certified payment gateway with tokenization.
        """,
        "use_cases": """
# Use Case Specifications

| Use Case ID | Use Case Name | Actor | Preconditions | Postconditions |
| :--- | :--- | :--- | :--- | :--- |
| **UC-HT-101** | Make Hotel Room Reservation | Guest | Room availability confirmed | Booking confirmed, confirmation email sent |
| **UC-HT-102** | Check Guest Into Room | Front Desk Agent | Reservation active, guest present | Room key issued, PMS status updated |
| **UC-HT-103** | Update Housekeeping Status | Housekeeper | Guest checked out | Room status set to 'Cleaning', then 'Ready' |

### Use Case Flow: UC-HT-101 (Make Hotel Room Reservation)
1. Guest selects dates and room type on the booking engine.
2. System checks real-time availability from the PMS inventory.
3. Guest selects room, enters personal details, and provides payment.
4. Payment is tokenized and processed via the payment gateway.
5. Confirmation email is sent with booking reference and cancellation policy.
        """,
        "user_stories": """
# User Stories & Acceptance Criteria

### US-HT-201: Dynamic Room Pricing
**As a** Revenue Manager
**I want to** automatically adjust room rates based on occupancy and demand signals
**So that** we maximize RevPAR during peak periods and maintain occupancy during slow seasons.

*Acceptance Criteria:*
- **AC1:** System checks occupancy levels every 4 hours and adjusts rates per active pricing rules.
- **AC2:** Rate changes are pushed to all booking channels within 10 minutes.
- **AC3:** Revenue Manager receives a daily rate optimization summary report.

---

### US-HT-202: Mobile Housekeeping Updates
**As a** Housekeeper
**I want to** update room cleaning status from my mobile device
**So that** front desk knows in real time which rooms are ready for check-in.

*Acceptance Criteria:*
- **AC1:** Housekeeper can set status to 'Cleaning', 'Inspecting', or 'Ready' from the mobile app.
- **AC2:** PMS room status updates within 30 seconds of housekeeper's action.
- **AC3:** Front desk receives a notification when a high-priority room is marked 'Ready'.
        """,
        "db_suggestions": """
# Database Design Suggestions

Suggested stack: **PostgreSQL** for the PMS core; **Redis** for real-time room availability cache across booking channels.

## Entity Relationship Outline
```mermaid
erDiagram
    ROOMS ||--o{ RESERVATIONS : booked_via
    GUESTS ||--o{ RESERVATIONS : makes
    RESERVATIONS ||--o{ INVOICES : billed_with
    GUESTS ||--|| LOYALTY_PROFILES : has
```

## SQL DDL Scripts
```sql
CREATE TABLE rooms (
    room_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_number VARCHAR(10) UNIQUE NOT NULL,
    room_type VARCHAR(50) NOT NULL,
    floor INT,
    base_rate NUMERIC(8,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'available'
);

CREATE TABLE reservations (
    reservation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    guest_id UUID NOT NULL,
    room_id UUID REFERENCES rooms(room_id),
    check_in_date DATE NOT NULL,
    check_out_date DATE NOT NULL,
    total_amount NUMERIC(10,2),
    status VARCHAR(20) DEFAULT 'confirmed',
    booked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
        """
    },
}


# =====================================================================
# 5.A  Project History Page — functions defined before sidebar render
# =====================================================================

def _load_and_open_project(proj):
    """
    Loads a project from the database (by numeric ID) or falls back to session state,
    then navigates to the dashboard page so the existing 8-tab viewer renders it.
    """
    proj_name = proj["name"]

    # Try DB first
    if database.DB_AVAILABLE and proj.get("id"):
        try:
            proj_data = database.get_project_with_requirements(proj["id"])
            if proj_data:
                st.session_state.projects[proj_name] = proj_data
                st.session_state.current_project = proj_name
                st.session_state.page = "dashboard"
                st.rerun()
                return
        except Exception as e:
            st.error(f"❌ Database error while loading '{proj_name}': {str(e)}")
            return

    # Fallback to already-loaded session state
    if proj_name in st.session_state.projects:
        st.session_state.current_project = proj_name
        st.session_state.page = "dashboard"
        st.rerun()
    else:
        st.warning(
            f"⚠️ '{proj_name}' is not available in memory and the database is offline. "
            "Please regenerate it from the Dashboard."
        )


def render_history_page():
    """
    Renders the full-featured Project History page.
    Features: stat cards, search, industry filter, sort, 3-col card grid,
    colour-coded badges, scope preview, one-click project reopen.
    """

    # ── Page Header ────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="margin-bottom: 2rem;">
        <h1 style="margin:0; font-size:2.2rem; font-weight:800; letter-spacing:-0.04em;">
            📚 Project <span class="text-gradient">History</span>
        </h1>
        <p style="margin:0.3rem 0 0 0; font-size:0.95rem; color:{text_muted}; font-weight:500;">
            Browse, search, and reopen all previously generated ERP requirement suites.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Fetch All Projects ─────────────────────────────────────────────────────
    all_projects = []
    fetch_error = None

    if database.DB_AVAILABLE:
        try:
            all_projects = database.list_projects_full()
        except Exception as e:
            fetch_error = str(e)

    # Session-state fallback when DB is unavailable or empty
    if not all_projects:
        all_projects = [
            {
                "id":               None,
                "name":             h["name"],
                "industry":         h.get("industry", "General"),
                "scope_preview":    (
                    st.session_state.projects.get(h["name"], {}).get("scope", "")[:155] + "…"
                    if st.session_state.projects.get(h["name"], {}).get("scope", "")
                    else "No scope details available."
                ),
                "feature_count":    len(st.session_state.projects.get(h["name"], {}).get("features", [])),
                "features":         st.session_state.projects.get(h["name"], {}).get("features", []),
                "has_requirements": h["name"] in st.session_state.projects,
                "created_at":       h.get("date", "Unknown"),
                "updated_date":     h.get("date", "Unknown"),
                "updated_at_full":  h.get("date", "Unknown"),
            }
            for h in st.session_state.history
        ]

    if fetch_error:
        st.warning(f"⚠️ Database error — showing session cache: {fetch_error}")
    elif not database.DB_AVAILABLE:
        st.info("ℹ️ SQL Server offline — showing session state projects only.")

    # ── Stats Bar ──────────────────────────────────────────────────────────────
    industries_set = sorted(set(p.get("industry", "General") for p in all_projects))
    docs_ready     = sum(1 for p in all_projects if p.get("has_requirements"))
    db_status_text = "🟢 Live" if database.DB_AVAILABLE else "🔴 Offline"

    sc1, sc2, sc3, sc4 = st.columns(4)
    for _col, _label, _val, _delta in [
        (sc1, "Total Projects",    str(len(all_projects)), "↑ All time"),
        (sc2, "Industries",        str(len(industries_set)), "→ Cross-domain"),
        (sc3, "Doc Suites Ready",  str(docs_ready),        "↑ 8-tab suites"),
        (sc4, "Database",          db_status_text,          "SQL Server"),
    ]:
        with _col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{_label}</div>
                <div class="metric-value" style="font-size:1.4rem;">{_val}</div>
                <div class="metric-delta delta-up">{_delta}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:1.5rem;'></div>", unsafe_allow_html=True)

    # ── Search, Filter & Sort Controls ────────────────────────────────────────
    fc1, fc2, fc3 = st.columns([5, 3, 2])
    with fc1:
        search_query = st.text_input(
            "Search", placeholder="🔍  Search by project name…",
            label_visibility="collapsed", key="hist_search_input"
        )
    with fc2:
        selected_industry = st.selectbox(
            "Industry", options=["All Industries"] + industries_set,
            label_visibility="collapsed", key="hist_industry_filter"
        )
    with fc3:
        sort_by = st.selectbox(
            "Sort", options=["Newest First", "Oldest First", "A → Z", "Z → A"],
            label_visibility="collapsed", key="hist_sort_order"
        )

    # ── Apply Filters & Sort ───────────────────────────────────────────────────
    filtered = all_projects[:]
    if search_query.strip():
        q = search_query.strip().lower()
        filtered = [p for p in filtered if q in p["name"].lower()]
    if selected_industry != "All Industries":
        filtered = [p for p in filtered if p.get("industry") == selected_industry]
    if sort_by == "Oldest First":
        filtered = list(reversed(filtered))
    elif sort_by == "A → Z":
        filtered = sorted(filtered, key=lambda p: p["name"].lower())
    elif sort_by == "Z → A":
        filtered = sorted(filtered, key=lambda p: p["name"].lower(), reverse=True)

    # ── Results Summary Banner ─────────────────────────────────────────────────
    db_label = "🟢 Live from SQL Server" if database.DB_AVAILABLE else "🔴 Session Cache (DB offline)"
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center;
        margin-bottom:1.5rem; padding:0.65rem 1rem; background:{bg_subtle};
        border:1px solid {border_color}; border-radius:10px;">
        <span style="font-size:0.85rem; color:{text_dim}; font-weight:500;">
            Showing <strong style="color:{text_color};">{len(filtered)}</strong> of
            <strong style="color:{text_color};">{len(all_projects)}</strong> projects
        </span>
        <span style="font-size:0.78rem; color:{text_dim};">{db_label}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Empty State ────────────────────────────────────────────────────────────
    if not filtered:
        no_proj_hint = (
            "Generate your first project from the Dashboard."
            if not all_projects else
            "Try clearing the search field or selecting \"All Industries\"."
        )
        st.markdown(f"""
        <div class="empty-state">
            <div class="empty-state-icon">🔍</div>
            <h3 style="font-weight:700; margin:0.5rem 0; font-size:1.25rem;">No Projects Found</h3>
            <p style="color:{text_dim}; font-size:0.88rem; max-width:380px; line-height:1.5;">
                {no_proj_hint}
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Industry Colour Palette ────────────────────────────────────────────────
    IND_COLORS = {
        "FinTech":                     ("#34d399", "rgba(16,185,129,0.10)"),
        "Healthcare":                  ("#60a5fa", "rgba(96,165,250,0.10)"),
        "E-commerce":                  ("#f472b6", "rgba(244,114,182,0.10)"),
        "Supply Chain":               ("#fb923c", "rgba(251,146,60,0.10)"),
        "EdTech":                      ("#a78bfa", "rgba(167,139,250,0.10)"),
        "Manufacturing & Production": ("#f59e0b", "rgba(245,158,11,0.10)"),
        "Retail & POS":               ("#ec4899", "rgba(236,72,153,0.10)"),
        "Banking & Insurance":        ("#22d3ee", "rgba(34,211,238,0.10)"),
        "HR & Payroll":               ("#84cc16", "rgba(132,204,22,0.10)"),
        "Logistics & Transportation": ("#f97316", "rgba(249,115,22,0.10)"),
        "Agriculture & FarmTech":     ("#4ade80", "rgba(74,222,128,0.10)"),
        "Real Estate & PropTech":     ("#c084fc", "rgba(192,132,252,0.10)"),
        "Legal & Compliance":         ("#94a3b8", "rgba(148,163,184,0.10)"),
        "Government & Public Sector": ("#3b82f6", "rgba(59,130,246,0.10)"),
        "Hospitality & Tourism":      ("#fbbf24", "rgba(251,191,36,0.10)"),
        "General":                    ("#a5b4fc", "rgba(165,180,252,0.10)"),
    }
    DEFAULT_IND = ("#a5b4fc", "rgba(165,180,252,0.10)")

    # ── Project Card Grid (3 columns) ──────────────────────────────────────────
    GRID = 3
    for row_start in range(0, len(filtered), GRID):
        row_items = filtered[row_start: row_start + GRID]
        # Pad with None so grid always has GRID columns
        row_items += [None] * (GRID - len(row_items))
        grid_cols = st.columns(GRID)

        for col_idx, proj in enumerate(row_items):
            if proj is None:
                continue
            with grid_cols[col_idx]:
                ind           = proj.get("industry", "General")
                ind_color, ind_bg = IND_COLORS.get(ind, DEFAULT_IND)
                feat_n        = proj.get("feature_count", 0)
                has_docs      = proj.get("has_requirements", False)
                scope_text    = proj.get("scope_preview", "No scope details available.")
                date_label    = proj.get("updated_date", "—")

                docs_pill = (
                    '<span style="color:#34d399;font-size:0.72rem;font-weight:700;">● 8 Docs Ready</span>'
                    if has_docs else
                    f'<span style="color:{text_dim};font-size:0.72rem;">○ No Docs Yet</span>'
                )

                st.markdown(f"""
                <div style="
                    background:{card_color};
                    border:1px solid {border_color};
                    border-radius:16px;
                    padding:0 0 0.9rem 0;
                    margin-bottom:0.4rem;
                    position:relative;
                    overflow:hidden;
                ">
                    <div style="height:3px;
                        background:linear-gradient(90deg,#8b5cf6,#6366f1);
                        border-radius:16px 16px 0 0;
                        margin-bottom:1rem;">
                    </div>
                    <div style="padding:0 1.25rem;">
                        <div style="display:flex;justify-content:space-between;
                            align-items:center;margin-bottom:0.6rem;">
                            <span style="
                                font-size:0.72rem;font-weight:700;padding:3px 10px;
                                border-radius:20px;background:{ind_bg};color:{ind_color};
                                border:1px solid {ind_color}40;">{ind}</span>
                            <span style="font-size:0.72rem;color:{text_dim};">
                                📅 {date_label}</span>
                        </div>
                        <div style="font-size:0.98rem;font-weight:700;color:{text_color};
                            margin-bottom:0.5rem;line-height:1.3;">
                            ⚡ {proj['name']}
                        </div>
                        <div style="font-size:0.78rem;color:{text_dim};line-height:1.55;
                            margin-bottom:0.9rem;min-height:3.6rem;">
                            {scope_text}
                        </div>
                        <div style="display:flex;justify-content:space-between;align-items:center;
                            padding-top:0.65rem;border-top:1px solid {border_subtle};">
                            <span style="font-size:0.72rem;color:{text_dim};">
                                📦 {feat_n} Module{"s" if feat_n != 1 else ""}
                            </span>
                            {docs_pill}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Unique key: use DB id when available, else a stable hash of the name
                _key_id = proj.get("id") or (abs(hash(proj["name"])) % 99999)
                if st.button(
                    "Open Project →",
                    key=f"hist_open_{_key_id}_{row_start}_{col_idx}",
                    use_container_width=True
                ):
                    _load_and_open_project(proj)


# Left Sidebar Setup
with st.sidebar:

    st.markdown("""
    <div class="sidebar-logo">
        <div class="logo-badge">⚡</div>
        <div class="logo-text">ReqFlow <span class="text-gradient">AI</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="sidebar-heading">Navigation</div>', unsafe_allow_html=True)

    # Active page indicator pill
    if st.session_state.page == "dashboard":
        _active_label = "Dashboard"
    elif st.session_state.page == "history":
        _active_label = "Project History"
    else:
        _active_label = "User Management"

    st.markdown(f"""
    <div style="background:rgba(139,92,246,0.08);border:1px solid rgba(139,92,246,0.2);
        border-radius:8px;padding:0.4rem 0.75rem;margin-bottom:0.6rem;
        font-size:0.78rem;color:#a78bfa;font-weight:600;">
        📍 {_active_label}
    </div>
    """, unsafe_allow_html=True)

    if st.button("🏠 Dashboard", use_container_width=True, key="nav_btn_dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

    if st.button("📚 Project History", use_container_width=True, key="nav_btn_history"):
        st.session_state.page = "history"
        st.rerun()
        
    if auth.has_permission(["Admin"]):
        if st.button("👥 User Management", use_container_width=True, key="nav_btn_users"):
            st.session_state.page = "user_management"
            st.rerun()

    # ── Workspace section: only shown on Dashboard page ────────────────────────
    if st.session_state.page == "dashboard":
        st.markdown('<div class="sidebar-heading">Active Workspace</div>', unsafe_allow_html=True)

        # Project Settings Sidebar Form
        if database.DB_AVAILABLE:
            history_names = [h["name"] for h in st.session_state.history]
            all_proj_names = sorted(list(set(list(st.session_state.projects.keys()) + history_names)))
        else:
            all_proj_names = list(st.session_state.projects.keys())

        proj_options = ["Create New Project"] + all_proj_names

        # Calculate default index to maintain selection after generation/reload
        default_index = 0
        if st.session_state.current_project in proj_options:
            default_index = proj_options.index(st.session_state.current_project)

        selected_proj = st.selectbox(
            "Select Active Project",
            options=proj_options,
            index=default_index,
            label_visibility="collapsed"
        )

        if selected_proj != "Create New Project":
            st.session_state.current_project = selected_proj
            # If the project is in history/db but not loaded in memory, fetch it
            if database.DB_AVAILABLE and selected_proj not in st.session_state.projects:
                try:
                    proj_data = database.get_project_by_name(selected_proj)
                    if proj_data:
                        st.session_state.projects[selected_proj] = proj_data
                except Exception as e:
                    st.sidebar.error(f"Error loading project details: {str(e)}")
        else:
            st.session_state.current_project = None

        st.markdown('<div class="sidebar-heading">Workspace Stats</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Docs", len(st.session_state.projects) + 3, help="Count of generated requirement sets")
        with col2:
            st.metric("Credits Left", f"{st.session_state.credits}/100")

        st.markdown('<div class="sidebar-heading">Generation History</div>', unsafe_allow_html=True)

        for item in st.session_state.history:
            st.markdown(f"""
            <div class="history-item">
                <span class="history-name">⚡ {item['name']}</span>
                <span class="history-meta">
                    <span>{item['industry']}</span>
                    <span>{item['date']}</span>
                </span>
            </div>
            """, unsafe_allow_html=True)

    # ── Settings: always visible on both pages ─────────────────────────────────
    st.markdown('<div class="sidebar-heading">Settings</div>', unsafe_allow_html=True)

    # Theme Toggle button inside sidebar
    theme_btn_label = "☀️ Switch to Light Mode" if IS_DARK else "🌙 Switch to Dark Mode"
    if st.button(theme_btn_label, use_container_width=True, key="sidebar_theme_toggle"):
        toggle_theme()
        st.rerun()

    st.markdown("""
    <div class="credit-box">
        <div class="credit-title">ReqFlow Premium Enterprise</div>
        <div class="credit-progress">
            <div class="credit-fill" style="width: 95%;"></div>
        </div>
        <div class="credit-foot">
            <span>SaaS Plan: Active</span>
            <span>95% Remaining</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Place user profile and sign out at the very bottom
    auth.render_user_profile()

# ─── Page Router ──────────────────────────────────────────────────────────────
if st.session_state.page == "user_management":
    if auth.has_permission(["Admin"]):
        st.markdown("""
        <div style="margin-bottom: 2rem;">
            <h1 style="margin: 0; font-size: 2.2rem; font-weight: 800; tracking: -0.04em;">
                User <span class="text-gradient">Management</span>
            </h1>
            <p style="margin: 0.2rem 0 1.5rem 0; font-size: 0.95rem; color: #a5b4fc; font-weight: 500;">
                Add new team members and manage role-based access.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Center the registration page for better look on wide screens
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            auth.render_registration_page()
    else:
        st.error("You do not have permission to view this page.")
    st.stop()

# History page renders completely independently; st.stop() prevents the
# dashboard code below from executing when on the history page.
if st.session_state.page == "history":
    render_history_page()
    st.stop()

# Main Application Frame Header
head_left, head_right = st.columns([10, 2])
with head_left:
    st.markdown("""
    <h1 style="margin: 0; font-size: 2.2rem; font-weight: 800; tracking: -0.04em;">
        ReqFlow <span class="text-gradient">AI Enterprise Portal</span>
    </h1>
    <p style="margin: 0.2rem 0 1.5rem 0; font-size: 0.95rem; color: #a5b4fc; font-weight: 500;">
        Synthesize fully structured, compliant ERP Requirements documents instantly using domain-specific AI logic.
    </p>
    """, unsafe_allow_html=True)
with head_right:
    # Top-right quick diagnostic stats
    st.markdown(f"""
    <div style="text-align: right; padding-top: 0.5rem;">
        <span class="saas-badge saas-badge-purple">v1.2 Stable</span>
        <span class="saas-badge saas-badge-green" style="margin-left: 5px;">API Connected</span>
    </div>
    """, unsafe_allow_html=True)

# 6. Dashboard Summary Cards (KPIs)
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Documents Generated</div>
        <div class="metric-value">{len(st.session_state.projects) + 3}</div>
        <div class="metric-delta delta-up">↑ +2 this week</div>
    </div>
    """, unsafe_allow_html=True)
with kpi2:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-label">Avg. Generation Time</div>
        <div class="metric-value">4.2s</div>
        <div class="metric-delta delta-up">↓ -0.8s optimization</div>
    </div>
    """, unsafe_allow_html=True)
with kpi3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Active AI Credits</div>
        <div class="metric-value">{st.session_state.credits} / 100</div>
        <div class="metric-delta delta-up">→ Reset in 12 days</div>
    </div>
    """, unsafe_allow_html=True)
with kpi4:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-label">Estimated Hours Saved</div>
        <div class="metric-value">136 hrs</div>
        <div class="metric-delta delta-up">↑ +24 hrs saved</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

# 7. Workspace Configuration Form (full-width)

# Sidebar Form Logic Configuration
with st.container():
    st.markdown("""
    <div class="saas-card form-container">
        <div class="saas-card-title">📝 Workspace Configuration</div>
        <div class="saas-card-subtitle">Define target scope and core parameters to compile specifications.</div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        # Form fields
        proj_name_input = st.text_input(
            "Project Name",
            value="" if not st.session_state.current_project else st.session_state.current_project,
            placeholder="e.g., Nexus Retail Ledger, EPL Inventory, MedShield EHR..."
        )
        
        industry_options = [
            "— Select Industry —",
            "FinTech", "E-commerce", "Healthcare", "Supply Chain", "EdTech",
            "Manufacturing & Production", "Retail & POS", "Banking & Insurance",
            "HR & Payroll", "Logistics & Transportation", "Agriculture & FarmTech",
            "Real Estate & PropTech", "Legal & Compliance",
            "Government & Public Sector", "Hospitality & Tourism",
        ]
        industry_input = st.selectbox(
            "Industry Domain",
            options=industry_options,
            index=0
        )
        
        # Load features based on selected industry
        industry_key = industry_input if industry_input != "— Select Industry —" else None
        available_features = INDUSTRIES.get(industry_key, {}).get("features", []) if industry_key else []
        
        features_selected = st.multiselect(
            "Target Core Modules",
            options=available_features,
            default=[],
            placeholder="Select an Industry Domain first..."
        )
        
        scope_details = st.text_area(
            "Project Scope & Context Details",
            value="",
            height=130,
            placeholder="Describe your project scope, database constraints, transactional requirements, target users..."
        )
        
        creativity_level = st.slider(
            "AI Depth & Detail Level",
            min_value=0.0,
            max_value=1.0,
            value=0.8,
            step=0.1,
            help="High values produce longer descriptions, low values generate terse compliance summaries."
        )
        
        generate_btn = False
        if auth.has_permission(["Admin", "Business Analyst"]):
            generate_btn = st.button("✨ Generate ERP Requirements", use_container_width=True)
        else:
            st.info("Your role does not have permission to generate new requirements.")

# 8. Requirement Output Hub (full-width, below form)
with st.container():
    st.markdown("""
    <div class="saas-card">
        <div class="saas-card-title">🔮 Requirement Output Hub</div>
        <div class="saas-card-subtitle">Interactive compilation of Business and Technical Specifications.</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Process Generate trigger
    if generate_btn:
        if not proj_name_input.strip():
            st.error("Please provide a valid Project Name to proceed.")
        else:
            with st.spinner("For ERP specification (BRD, SRS, Use Case, User Story, DB, KPI, Workflow, Report)... documents are being created."):
                try:
                    # Call Gemini service to generate all 8 requirements sections
                    requirements = gemini_service.generate_erp_requirements(
                        project_name=proj_name_input,
                        industry=industry_input,
                        features=features_selected,
                        scope_details=scope_details,
                        creativity_level=creativity_level
                    )
                    
                    # Save requirements details to state
                    st.session_state.projects[proj_name_input] = {
                        "industry": industry_input,
                        "scope": scope_details,
                        "features": features_selected,
                        "brd": requirements["brd"],
                        "srs": requirements["srs"],
                        "use_cases": requirements["use_cases"],
                        "user_stories": requirements["user_stories"],
                        "db_suggestions": requirements["database_design"],
                        "kpis": requirements["kpis"],
                        "workflow": requirements["workflow"],
                        "reports": requirements["reports"],
                        "timestamp": datetime.now().strftime("%b %d, %H:%M")
                    }
                    st.session_state.current_project = proj_name_input
                    st.session_state.credits = max(0, st.session_state.credits - 10)
                    
                    # Persist to database if online
                    if database.DB_AVAILABLE:
                        try:
                            database.save_full_generation(
                                project_name=proj_name_input,
                                industry=industry_input,
                                scope_details=scope_details,
                                features=features_selected,
                                creativity_level=creativity_level,
                                requirements=requirements
                            )
                            st.success(f"✨ Project '{proj_name_input}' and generated documents saved to SQL Server successfully!")
                        except Exception as db_err:
                            st.warning(f"⚠️ Project generated successfully but database persistence failed: {str(db_err)}")

                    # Add to history if not already there
                    history_names = [h["name"] for h in st.session_state.history]
                    if proj_name_input not in history_names:
                        st.session_state.history.insert(0, {
                            "name": proj_name_input,
                            "industry": industry_input,
                            "date": "Today"
                        })
                    
                    st.toast("ERP Specification Suite successfully compiled!", icon="🚀")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to generate ERP Requirements with Gemini: {str(e)}")

    # Determine what project to display
    active_project_data = None
    if st.session_state.current_project:
        if st.session_state.current_project in st.session_state.projects:
            active_project_data = st.session_state.projects[st.session_state.current_project]
        elif database.DB_AVAILABLE:
            try:
                proj_data = database.get_project_by_name(st.session_state.current_project)
                if proj_data:
                    st.session_state.projects[st.session_state.current_project] = proj_data
                    active_project_data = proj_data
            except Exception as e:
                st.warning(f"Failed to load project details from database: {str(e)}")
        
    if not active_project_data:
        # Display onboarding card/state
        st.markdown(f"""
        <div class="empty-state">
            <div class="empty-state-icon">🔮</div>
            <h3 style="font-weight: 700; margin: 0.5rem 0; font-size: 1.25rem;">ReqFlow AI Sandbox Active</h3>
            <p style="color: {text_dim}; font-size: 0.88rem; max-width: 420px; line-height: 1.4; margin-bottom: 1.5rem;">
                No active project is selected. Configure your workspace details in the left configuration panel and press <strong>Generate ERP Requirements</strong> to create your document suite.
            </p>
            <div style="background-color: {bg_subtle}; padding: 0.85rem 1rem; border-radius: 10px; border: 1px solid {border_subtle}; display: flex; align-items: center; gap: 8px;">
                <span class="saas-badge saas-badge-purple">Sample View</span>
                <span style="font-size: 0.8rem; font-weight: 500; color: {text_color};">Select a history project or build a new one to unlock tabs.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Display sample overview metrics details
        st.markdown("<h4 style='font-size: 1rem; font-weight: 700; margin-top: 1.5rem;'>📈 AI Performance & Resource Allocation</h4>", unsafe_allow_html=True)
        # Add a dummy plotly chart to make it look like a fully fledged SaaS dashboard
        categories = ['Functional Requirements', 'Security Architecture', 'Database Schema', 'Integrations', 'System Testing']
        values = [35, 20, 15, 18, 12]
        fig = px.pie(
            names=categories,
            values=values,
            hole=0.6,
            color_discrete_sequence=['#8b5cf6', '#6366f1', '#a78bfa', '#c084fc', '#818cf8']
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit, sans-serif", color="#7c8ba1" if IS_DARK else "#6b7280", size=10),
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            )
        )
        fig.update_traces(
            textinfo="percent",
            hoverinfo="label+percent",
            marker=dict(line=dict(color=card_color, width=2))
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        
    else:
        # Show Tab view when project data is loaded
        st.markdown(f"""
        <div style="background-color: {bg_subtle}; padding: 0.75rem 1rem; border-radius: 12px; border: 1px solid {border_color}; margin-bottom: 1.25rem; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span style="font-size: 0.8rem; font-weight: 500; color: {text_dim};">Current Project:</span>
                <span style="font-size: 0.88rem; font-weight: 700; color: #8b5cf6; margin-left: 4px;">{st.session_state.current_project}</span>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
                <span class="saas-badge saas-badge-green">{active_project_data['industry']}</span>
                <span style="font-size: 0.72rem; color: {text_dim};">{active_project_data['timestamp']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Render the 8 specification tabs
        tab_brd, tab_srs, tab_use_cases, tab_user_stories, tab_db, tab_kpi, tab_wf, tab_rep = st.tabs([
            "📂 BRD", "📝 SRS", "🔄 Use Cases", "👥 User Stories", "💾 Database Suggestions", "📊 KPIs", "⚙️ Workflows", "📋 Reports"
        ])
        
        with tab_brd:
            st.markdown(active_project_data["brd"])
            
        with tab_srs:
            st.markdown(active_project_data["srs"])
            
        with tab_use_cases:
            st.markdown(active_project_data["use_cases"])
            
        with tab_user_stories:
            st.markdown(active_project_data["user_stories"])
            
        with tab_db:
            st.markdown(active_project_data["db_suggestions"])
            
        with tab_kpi:
            st.markdown(active_project_data.get("kpis", "*No KPIs generated.*"))
            
        with tab_wf:
            st.markdown(active_project_data.get("workflow", "*No workflow generated.*"))
            
        with tab_rep:
            st.markdown(active_project_data.get("reports", "*No reports generated.*"))
            
        # Overall Export Suite Action
        st.markdown("<hr style='margin: 1.5rem 0; border: 0; border-top: 1px solid var(--border);'>", unsafe_allow_html=True)
        
        # Unified export control center
        col_export_label, col_export_btn = st.columns([2, 1])
        with col_export_label:
            st.markdown(f"""
            <div style="display:flex; flex-direction:column; justify-content:center; height:100%;">
                <h4 style="margin:0; font-size:1.05rem; font-weight:700; color:{text_color};">📂 Export Requirements Suite</h4>
                <p style="margin:0; font-size:0.8rem; color:{text_dim};">Download single modules or the complete suite in PDF, Word, Excel, or Markdown format.</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col_export_btn:
            with st.popover("📥 Export Documents", use_container_width=True):
                st.markdown("### 📥 Document Export Control Center")
                st.write("Configure your document export preferences:")
                
                export_doc_type = st.selectbox(
                    "Document Selection",
                    options=[
                        "Full Requirement Suite",
                        "BRD",
                        "SRS",
                        "Use Cases",
                        "User Stories",
                        "Database Design",
                        "KPI",
                        "Workflow",
                        "Reports"
                    ],
                    key="export_doc_type_select"
                )
                
                export_format = st.selectbox(
                    "Select Format",
                    options=["PDF", "DOCX", "Excel", "Markdown"],
                    key="export_format_select"
                )
                
                try:
                    payload, filename, mime = export_manager.get_export_data(
                        project_name=st.session_state.current_project,
                        industry=active_project_data["industry"],
                        timestamp=active_project_data["timestamp"],
                        doc_type=export_doc_type,
                        format_type=export_format,
                        project_data=active_project_data
                    )
                    
                    if auth.has_permission(["Admin", "Business Analyst"]):
                        st.download_button(
                            label=f"💾 Download {export_format}",
                            data=payload,
                            file_name=filename,
                            mime=mime,
                            use_container_width=True,
                            key="btn_dl_unified",
                            on_click=log_download_callback,
                            args=(st.session_state.current_project, export_doc_type, export_format.lower(), str(payload)[:1000])
                        )
                    else:
                        st.info("Your role does not have permission to export documents.")
                except Exception as e:
                    st.error(f"Export Compilation Error: {str(e)}")
