<!-- TOC -->


# Service Governance Dashboard

A professional **SLA Compliance Monitoring** and **KPI Visualization** platform built with Python and Plotly Dash. This project demonstrates advanced data engineering, ITIL-aligned governance, and the orchestration of complex service metrics into actionable business intelligence.

---
## 📊 Overview

In IT service management, without a structured approach, critical problems take too long to resolve. This dashboard serves as a "Technical Bridge" between raw incident data and executive decision-making. By automating the tracking of Service Level Agreements (SLAs), it ensures that business continuity plans are backed by real-time data rather than assumptions.

---
## Version 
**1.0**

---
## 🎯 Objectives & Key Features

### 1. SLA Compliance by Priority

Monitors performance against established goals (e.g., 90% Target) across different ITIL priority levels.

- **Business Impact**: Prevents critical delays in the business continuity plan by identifying which priority tiers require resource reallocation.

### 2. MTTR Trend Analysis (Mean vs. Median)

A sophisticated bubble-chart visualization where marker size indicates incident volume.

- **Mean**: Represents total labor and technical debt.
- **Median**: Represents the "Typical" customer experience, filtering out extreme outliers.
- **Strategic Advantage**: Identifies "Stress Test" scenarios where performance degrades as volume increases, and pinpoints recurring pressure points like "Patch Tuesday."

### 3. Monthly First Contact Resolution (FCR)

Uses a **speedometer-style gauge** to track a 95% target.

- **Visual Benchmarking**: Red/Yellow/Green zones provide instant performance context.
- **Prevention of Escalation**: Validates that L1 agents handled issues end-to-end by verifying that the `First Assignment Group` matches the `Resolving Group`.
- **Delta Tracking**: Real-time indicators showing if performance improved or declined compared to the previous month.

---
## 🛠️ Technical Implementation & Architecture

### System Integration Map

The project follows a clean Separation of Concerns architecture:

```
graph TD
A[Raw Data: cleaned_6_months.xlsx] --> B[calculations.py]
B -->|Business Logic: ITIL Priority Matrix| C[Data Processing]
C -->|Regional Dist. Rules| D[dashboard_app.py]
D --> E[Interactive Dash UI]subgraph "Data Engineering Layer"
B
C
end
```

### Advanced Data Logic

- **Operational Fairness**: Calculations are based strictly on **Swedish Business Hours** (Mon-Fri 07-18, Sat-Sun 08-16). This ensures engineers are not "penalized" for tickets sitting in queues while the office is closed.
- **Data Masking (PII Protection)**: Includes a specialized script that scrubs Personally Identifiable Information using Regex (`(?i)company_name`) and generates standardized incident keys for data ethics compliance.

---
### 🚀 Key Strengths & Skills Demonstrated

- **Technical Literacy**: Programmatic manipulation of large `.xlsx` datasets and ServiceNow metrics.
- **Governance & Operational Control**: Calculating MTTR and SLA independently to ensure unbiased vendor reporting.
- **Data Quality & Ethics**: Implementation of workforce management logic and robust PII anonymization for public-facing reporting.
- **Vendor Audit Readiness**: Includes a `Vendor_Audit_Template.md` for Service Improvement Plans (SIP) when vendors fall below targets.

---
### 📁 Project Structure

```
Dashboard_Project
├── calculations.py        # Heavy lifting: MTTR, SLA, and Business Hour logic
├── dashboard_app.py       # Presentation layer: Dash Layout & Callbacks
├── requirements.txt       # Dependencies (Dash, Pandas, Plotly, etc.)
├── Vendor_Audit_Template.md # Vendor Audit Template
├── data/
│   ├── cleaned_6_months.xlsx
│   └── anonymization_assets/
├── Media/                 # Screenshots of FCR, MTTR, and SLA Graphs
├── scripts/
│   ├── data_cleaner.py    # PII Scrubbing & Data Masking script
│   └── ServiceNow_metrics.py
└── workflows/
└── schedule.yml       # Automated reporting triggers
```

---
### :warning: Disclaimer

All data utilized in this project is mock data generated for demonstration purposes. No real-world company data or sensitive information was used in the creation of this dashboard.

---
### :badger: Getting Started


#### Prerequisites

- Python 3.9+
- An Excel file named `All inc 6 months.xlsx` placed in the /data folder.


#### Installation & Setup
1. **Clone the repository**:
```
git clone https://github.com/your-username/Dashboard_Project.git
cd Dashboard_Project
```

2. **Install dependencies**:
```
pip install -r requirements.txt
```

3. **Run the Data Masking script (Optional)**: If you need to anonymize new raw data before launching the dashboard:
```
python scripts/data_cleaner.py
```

4. Launch the Dashboard:
```
python dashboard_app.py
```

The dashboard will be available at `http://127.0.0.1:8050/` in your web browser.

---
## :unicorn: Author
**Sandra van Buggenum**

- GitHub: [SnowY4you](https://github.com/SnowY4you)
- LinkedIn: [Sandra van Buggenum](https://www.linkedin.com/in/sandravanbuggenum)

---
## Changelog


### 1.0.0 – 2025-12-24
- Initial release