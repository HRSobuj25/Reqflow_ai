import streamlit as st
import pandas as pd
import numpy as np
import time
import json
import io
from datetime import datetime
import plotly.express as px
import gemini_service
import database
import importlib
importlib.reload(gemini_service)
importlib.reload(database)

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
        background-color: {bg_color} !important;
        color: {text_color} !important;
        font-family: 'Cambria', Georgia, serif !important;
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
    }
}

# 5. Core Layout Architecture


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
        "FinTech":       ("#34d399", "rgba(16,185,129,0.10)"),
        "Healthcare":    ("#60a5fa", "rgba(96,165,250,0.10)"),
        "E-commerce":    ("#f472b6", "rgba(244,114,182,0.10)"),
        "Supply Chain":  ("#fb923c", "rgba(251,146,60,0.10)"),
        "EdTech":        ("#a78bfa", "rgba(167,139,250,0.10)"),
        "General":       ("#a5b4fc", "rgba(165,180,252,0.10)"),
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
        <div class="logo-badge">R</div>
        <div class="logo-text">ReqFlow <span class="text-gradient">AI</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="sidebar-heading">Navigation</div>', unsafe_allow_html=True)

    # Active page indicator pill
    _active_label = "Dashboard" if st.session_state.page == "dashboard" else "Project History"
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

# ─── Page Router ──────────────────────────────────────────────────────────────
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

# 7. Workspace Layout Splits
col_form, col_display = st.columns([5, 7])

# Sidebar Form Logic Configuration
with col_form:
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
            value="Zenith Supply Logistics" if not st.session_state.current_project else st.session_state.current_project,
            placeholder="e.g., Nexus Retail Ledger"
        )
        
        industry_input = st.selectbox(
            "Industry Domain",
            options=["FinTech", "E-commerce", "Healthcare", "Supply Chain", "EdTech"],
            index=3
        )
        
        # Load features based on industry
        industry_key = industry_input if industry_input != "Supply Chain" else "Supply Chain"
        available_features = INDUSTRIES[industry_key]["features"]
        
        features_selected = st.multiselect(
            "Target Core Modules",
            options=available_features,
            default=available_features[:3]
        )
        
        scope_details = st.text_area(
            "Project Scope & Context Details",
            value=INDUSTRIES[industry_key]["default_scope"],
            height=130,
            placeholder="Describe database constraints, transactional requirements, target users..."
        )
        
        creativity_level = st.slider(
            "AI Depth & Detail Level",
            min_value=0.0,
            max_value=1.0,
            value=0.8,
            step=0.1,
            help="High values produce longer descriptions, low values generate terse compliance summaries."
        )
        
        generate_btn = st.button("✨ Generate ERP Requirements", use_container_width=True)

# 8. Generation and tab preview block
with col_display:
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
            with st.spinner("Gemini AI synthesizing full ERP specifications (BRD, SRS, Use Cases, User Stories, DB, KPIs, Workflows, Reports)..."):
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
            st.download_button(
                label="📥 Export BRD to Markdown",
                data=active_project_data["brd"],
                file_name=f"{st.session_state.current_project.replace(' ', '_')}_BRD.md",
                mime="text/markdown",
                key="btn_dl_brd",
                on_click=log_download_callback,
                args=(st.session_state.current_project, "BRD", "md", active_project_data["brd"])
            )
            
        with tab_srs:
            st.markdown(active_project_data["srs"])
            st.download_button(
                label="📥 Export SRS to Markdown",
                data=active_project_data["srs"],
                file_name=f"{st.session_state.current_project.replace(' ', '_')}_SRS.md",
                mime="text/markdown",
                key="btn_dl_srs",
                on_click=log_download_callback,
                args=(st.session_state.current_project, "SRS", "md", active_project_data["srs"])
            )
            
        with tab_use_cases:
            st.markdown(active_project_data["use_cases"])
            st.download_button(
                label="📥 Export Use Cases to Markdown",
                data=active_project_data["use_cases"],
                file_name=f"{st.session_state.current_project.replace(' ', '_')}_UseCases.md",
                mime="text/markdown",
                key="btn_dl_uc",
                on_click=log_download_callback,
                args=(st.session_state.current_project, "Use Cases", "md", active_project_data["use_cases"])
            )
            
        with tab_user_stories:
            st.markdown(active_project_data["user_stories"])
            st.download_button(
                label="📥 Export User Stories to Markdown",
                data=active_project_data["user_stories"],
                file_name=f"{st.session_state.current_project.replace(' ', '_')}_UserStories.md",
                mime="text/markdown",
                key="btn_dl_us",
                on_click=log_download_callback,
                args=(st.session_state.current_project, "User Stories", "md", active_project_data["user_stories"])
            )
            
        with tab_db:
            st.markdown(active_project_data["db_suggestions"])
            st.download_button(
                label="📥 Export Database Suggestions to Markdown",
                data=active_project_data["db_suggestions"],
                file_name=f"{st.session_state.current_project.replace(' ', '_')}_Database.md",
                mime="text/markdown",
                key="btn_dl_db",
                on_click=log_download_callback,
                args=(st.session_state.current_project, "Database Suggestions", "md", active_project_data["db_suggestions"])
            )
            
        with tab_kpi:
            st.markdown(active_project_data.get("kpis", "*No KPIs generated.*"))
            st.download_button(
                label="📥 Export KPIs to Markdown",
                data=active_project_data.get("kpis", ""),
                file_name=f"{st.session_state.current_project.replace(' ', '_')}_KPIs.md",
                mime="text/markdown",
                key="btn_dl_kpis",
                on_click=log_download_callback,
                args=(st.session_state.current_project, "KPIs", "md", active_project_data.get("kpis", ""))
            )
            
        with tab_wf:
            st.markdown(active_project_data.get("workflow", "*No workflow generated.*"))
            st.download_button(
                label="📥 Export Workflow to Markdown",
                data=active_project_data.get("workflow", ""),
                file_name=f"{st.session_state.current_project.replace(' ', '_')}_Workflow.md",
                mime="text/markdown",
                key="btn_dl_wf",
                on_click=log_download_callback,
                args=(st.session_state.current_project, "Workflow", "md", active_project_data.get("workflow", ""))
            )
            
        with tab_rep:
            st.markdown(active_project_data.get("reports", "*No reports generated.*"))
            st.download_button(
                label="📥 Export Reports Suggestions to Markdown",
                data=active_project_data.get("reports", ""),
                file_name=f"{st.session_state.current_project.replace(' ', '_')}_Reports.md",
                mime="text/markdown",
                key="btn_dl_reports",
                on_click=log_download_callback,
                args=(st.session_state.current_project, "Reports Suggestions", "md", active_project_data.get("reports", ""))
            )
            
        # Overall Export Suite Action
        st.markdown("<hr style='margin: 1.5rem 0; border: 0; border-top: 1px solid var(--border);'>", unsafe_allow_html=True)
        
        # Combine entire project into a single Markdown document for the complete download suite
        combined_markdown = f"# ReqFlow AI Full Specification Suite: {st.session_state.current_project}\n"
        combined_markdown += f"Industry: {active_project_data['industry']}\n"
        combined_markdown += f"Generated: {active_project_data['timestamp']}\n\n"
        combined_markdown += "---\n\n"
        
        combined_markdown += f"# Business Requirements Document (BRD)\n\n{active_project_data['brd']}\n\n---\n\n"
        combined_markdown += f"# Software Requirements Specification (SRS)\n\n{active_project_data['srs']}\n\n---\n\n"
        combined_markdown += f"# Use Case Specifications\n\n{active_project_data['use_cases']}\n\n---\n\n"
        combined_markdown += f"# User Stories & Acceptance Criteria\n\n{active_project_data['user_stories']}\n\n---\n\n"
        combined_markdown += f"# Database Design Suggestions\n\n{active_project_data['db_suggestions']}\n\n---\n\n"
        
        if "kpis" in active_project_data:
            combined_markdown += f"# KPI Suggestions\n\n{active_project_data['kpis']}\n\n---\n\n"
        if "workflow" in active_project_data:
            combined_markdown += f"# Workflow Suggestions\n\n{active_project_data['workflow']}\n\n---\n\n"
        if "reports" in active_project_data:
            combined_markdown += f"# Reports Suggestions\n\n{active_project_data['reports']}\n"
        
        st.download_button(
            label="📥 Export Complete Requirement Suite (Markdown)",
            data=combined_markdown,
            file_name=f"{st.session_state.current_project.replace(' ', '_')}_Complete_Suite.md",
            mime="text/markdown",
            use_container_width=True,
            key="btn_dl_suite",
            on_click=log_download_callback,
            args=(st.session_state.current_project, "Complete Suite", "md", combined_markdown)
        )
