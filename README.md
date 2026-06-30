# ReqFlow AI - Modern ERP Requirement Dashboard

ReqFlow AI is a high-fidelity SaaS dashboard built with **Streamlit** and styled using a customized purple gradient theme. It utilizes mock AI modules (which can be mapped directly to actual LLM APIs like Gemini) to generate comprehensive Business Requirement Documents (BRD), Software Requirement Specifications (SRS), Use Cases, User Stories, and Database schemas for multiple industries including FinTech, E-commerce, Healthcare, Supply Chain, and EdTech.

## Features

- **Modern SaaS Aesthetics**: Purple gradient colors, rounded cards, micro-animations, custom tables, and status badges.
- **Dual-Mode Theme support**: Complete Light and Dark mode layout styles instantly switchable.
- **Dashboard Overview Metrics**: KPI summary metrics monitoring generated document counts, credits, and time savings.
- **Dynamic Configuration Form**: Set project names, target industry, select specific ERP feature modules, and set AI details.
- **Multi-Tab Preview Engine**: Displays customized, formatted Markdown requirements containing detailed process and relationship flowcharts (via Mermaid syntax).
- **One-Click Exports**: Export single spec documents or download the complete suite in standard Markdown files.

## Local Setup

### 1. Install Dependencies
Make sure you have Python 3.9+ installed. Install the requirements:
```bash
pip install -r requirements.txt
```

### 2. Run the Application
Start the Streamlit application:
```bash
streamlit run app.py
```

### 3. Open in Browser
By default, the application will launch at `http://localhost:8501`.
