<p align="center">
  <img src="assets/banner.svg" alt="Atmosphere360: Mumbai - Air Quality & Health Action Platform" width="100%">
</p>

<p align="center">
  <img alt="Status" src="https://img.shields.io/badge/status-prototype-orange">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="Streamlit" src="https://img.shields.io/badge/app-Streamlit-ff4b4b">
  <img alt="Data" src="https://img.shields.io/badge/data-CPCB%20%2B%20Open--Meteo%20%2B%20SerpApi%20%2B%20Groq-1b7f8c">
  <img alt="Licence" src="https://img.shields.io/badge/licence-MIT-green">
  <img alt="Hackathon" src="https://img.shields.io/badge/Built%20for-Beyond%209TO5%20Buildathon%20Mumbai%202026-purple">
</p>

<p align="center">
  <a href="https://atmosphere360aweb.streamlit.app/"><b>Live Demo (v1)</b></a> &nbsp;|&nbsp;
  <a href="#quick-start">Quick Start</a> &nbsp;|&nbsp;
  <a href="#three-modes">Three Modes</a> &nbsp;|&nbsp;
  <a href="#architecture">Architecture</a> &nbsp;|&nbsp;
  <a href="reports/EVALUATION.md">Evaluation Report</a>
</p>

**Atmosphere360** transforms Mumbai's air quality intelligence into a complete **AI-powered Air Quality & Health Action Platform** serving three audiences through one connected journey:

> **Detect pollution → Understand personal risk → Recommend action → Find suitable products → Monitor improvement**

Built for **Beyond 9TO5 Buildathon — Mumbai Edition (Nov 22, 2026)** at Paytm, Andheri.

---

## 🎯 Three Modes, One Intelligence Engine

| Mode | Audience | Modules | Value |
|------|----------|---------|-------|
| **🏠 Citizen** | Public | My Air, AirCare AI, PurifierMatch, CivicPulse | Free + affiliate revenue |
| **🏛️ Officer** | BMC/MPCB | Command Center, Expected Alerts, Team Deployment, Complaint Queue | Institutional SaaS |
| **🏢 Enterprise** | Schools, Hospitals, Offices | AirSense (Indoor IAQ), Building Portfolio | Per-building subscription |

All modes share: **CPCB historical (3yr) + Open-Meteo live forecast + SerpApi live data + LightGBM forecasting + Groq LLM**

---

## 🚀 Key Differentiators

| Feature | Description |
|---------|-------------|
| **PurifierMatch** | CADR calculator (room volume × ACH / 60) → 3 tiered recommendations → side-by-side TCO comparison → live multi-API pricing (SerpApi Shopping + Search) |
| **AirCare AI Chatbot** | Conversational Groq LLM with live AQI, 48h forecast, news, CPCB bulletins context |
| **Expected Alerts Engine** | Real-time AQI forecast + wind stagnation + persistence + citizen complaints → auto-generates High Alert/Watch/Advisory |
| **Team Deployment** | One-click dispatch → track Dispatched→On-Site→Verified → auto-links complaints |
| **Admin Panel** | 4 tiers (Free/Pro/Enterprise/Officer) with feature flags, rate limits, pricing, revenue analytics |
| **Live City Pulse** | Sidebar strip: live PM2.5/PM10/AQI vs 3-year baseline deltas, wind dispersion, news |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Atmosphere360 Platform                       │
├──────────────────┬────────────────────┬────────────────────────┤
│   🏠 CITIZEN     │    🏛️ OFFICER      │    🏢 ENTERPRISE       │
│  • My Air       │  • Command Center  │  • AirSense Monitor    │
│  • AirCare AI   │  • Expected Alerts │  • Building Portfolio  │
│  • PurifierMatch│  • Team Deploy     │  • Indoor IAQ + Reports│
│  • CivicPulse   │  • Complaint Queue │                        │
└────────┬─────────┴────────┬──────────┴───────────┬────────────┘
         │                  │                      │
         └──────────────────┴──────────────────────┘
                          │
         ┌────────────────▼────────────────┐
         │      SHARED INTELLIGENCE        │
         │  • CPCB 3-yr historical (parquet)│
         │  • Open-Meteo live forecast     │
         │  • LightGBM next-day AQI/severity│
         │  • Priority scoring (5 criteria)│
         │  • Groq LLM (recommendations)   │
         └────────────────┬────────────────┘
                          │
         ┌────────────────▼────────────────┐
         │       LIVE DATA LAYER           │
         │  • SerpApi (5 engines)          │
         │    - Google Search (alerts)     │
         │    - Google Maps (sources)      │
         │    - Google Shopping (prices)   │
         │    - Google News (bulletins)    │
         │    - Extract (CPCB live)        │
         │  • Open-Meteo Forecast + AQ API │
         │  • SQLite (complaints, teams,   │
         │    buildings, tiers, revenue)   │
         └─────────────────────────────────┘
```

---

## 📋 Module Overview

### 🏠 Citizen Mode
| Module | Features |
|--------|----------|
| **My Air** | Live AQI/PM2.5/PM10 + 3yr baseline deltas, Air Score (0-100), activity guidance, 48h forecast |
| **AirCare** | Groq LLM chatbot with live context (forecast, news, CPCB), context selector (home/office/school/outdoors), personalized checklist |
| **PurifierMatch** | CADR calculator → Budget/Balanced/Premium picks → working side-by-side comparison → TCO (device + filter + energy) → live SerpApi prices |
| **CivicPulse** | Photo + location complaints → AI categorization → reference ID (CP-YYYYMMDD-XXX) → status tracking (Submitted→Resolved) |

### 🏛️ Officer Mode
| Module | Features |
|--------|----------|
| **Command Center** | City hotspot map, top-5 priority zones, AI daily briefing (Groq), citizen complaint queue, SerpApi pollution source finder |
| **Expected Alerts** | Auto-generated from: AQI forecast >200, wind <8km/h, 3+ persistence days, 2+ complaints → High Alert / Watch / Advisory |
| **Team Deployment** | Dispatch teams (BMC Ward A/B, MPCB, Traffic, Fire) → link complaints → track status (Dispatched→On-Site→Verified) |
| **Route Planner** | Haversine nearest-neighbor tour for top-N zones + stop-by-stop itinerary |

### 🏢 Enterprise Mode
| Module | Features |
|--------|----------|
| **AirSense Monitor** | Register buildings/rooms → manual indoor PM2.5 entry → I/O ratio charts → WHO guideline overlays → Groq PDF reports |
| **Building Portfolio** | Cross-building dashboard with avg/max PM2.5, monitoring coverage, action status |

### 🔧 Admin Panel (Owner Only)
| Feature | Description |
|---------|-------------|
| **Tier Config** | Free/Pro/Enterprise/Officer → feature flags, rate limits, pricing |
| **Revenue Analytics** | 30-day MRR, by-tier/by-metric breakdown, affiliate commission tracking |
| **System Metrics** | Complaints, deployments, teams, alerts, readings, buildings |
| **API Status** | SerpApi, Groq, Open-Meteo connectivity check |

---

## 📊 Data & Models

| Data | Source | Coverage |
|------|--------|----------|
| Historical AQI | CPCB CAAQMS | 597,912 hourly records, 36 stations (30 active), 2021-2023 |
| Weather | Open-Meteo ERA5 | 26,280 hourly obs, Mumbai coords |
| Live Forecast | Open-Meteo API | 48h hourly: temp, humidity, wind, PM2.5, PM10, AQI |
| Live Prices | SerpApi Shopping | Real-time INR prices from Amazon/Flipkart/Croma |
| Live News | SerpApi News | Pollution bulletins, policy announcements |
| Pollution Sources | SerpApi Maps | Factories, construction, traffic near stations |

**Models:**
- **LightGBM L1 Residual** — Next-day AQI (MAE 18.83 vs 19.42 persistence on 2023 holdout)
- **Gradient Boosting Classifier** — Severe day (AQI>200) detection (Recall 0.87, PR-AUC 0.812)
- **Priority Score** — 5-criteria composite (Exposure 30%, Persistence 25%, Forecast 20%, Trend 15%, Gap 10%)

---

## ⚡ Quick Start

```bash
# 1. Clone and enter
git clone https://github.com/RatneshPathak/atmosphere360-2.0.git
cd atmosphere360-2.0

# 2. Configure API keys
cp .env.example .env
# Edit .env with:
# SERPAPI_KEY=your_serpapi_key    # Get 500 free credits: serpapi.com/beyond9to5mumbai500
# GROQ_API_KEY=your_groq_key      # Free: console.groq.com/keys

# 3. Install & run
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py              # Opens at http://localhost:8501
```

### Access Admin Panel
1. Mode selector (sidebar) → **🔧 Admin — Owner Panel**
2. Password: `atmosphere3602026` (change in production!)

---

## 🧪 Testing & Evaluation

```bash
# Run 40 unit/integration tests
python -m unittest discover tests

# Full evaluation (reproduces all metrics)
pip install -r requirements-dev.txt
python Evaluate.py --full

# Quick evaluation (~35s)
python Evaluate.py --quick
```

**Key Results (2023 Holdout):**
- Next-day AQI MAE: **18.83** (vs 19.42 persistence)
- Severe day Recall: **0.870**, PR-AUC: **0.812**
- Weekly inspection backtest: **+43% hit-rate lift** over random
- 80% prediction intervals: **73.8%** empirical coverage

---

## 📁 Repository Structure

```
atmosphere360-2.0/
├── app.py                      # Main Streamlit app (3-mode router)
├── config.py                   # Constants, tiers, API key helpers
├── requirements.txt            # Runtime deps
├── requirements-dev.txt        # Training/eval deps (LightGBM, etc.)
├── .env.example                # API key template
├── serpapi_client.py           # SerpApi wrapper (5 engines)
├── data/
│   ├── raw/                    # CPCB telemetry + Open-Meteo weather
│   └── processed/              # Parquets, precomputed predictions
├── src/
│   ├── ingest/
│   │   └── live_feed.py        # Open-Meteo + SerpApi + 3yr baseline
│   ├── llm/
│   │   └── groq_client.py      # Groq LLM (recommendations, briefings)
│   ├── utils/
│   │   └── cadr_calculator.py  # CADR = Volume × ACH / 60
│   ├── data/
│   │   └── sqlite_store.py     # Complaints, teams, deployments, tiers, revenue
│   ├── citizen/
│   │   ├── my_air.py           # Personal AQI + live deltas
│   │   ├── aircare.py          # AI chatbot (imports my_air)
│   │   └── purifier_match.py   # CADR recs + comparison + live prices
│   ├── officer/
│   │   ├── civic_pulse.py      # Complaint reporting + queue
│   │   └── command_center.py   # Alerts + team deployment
│   ├── enterprise/
│   │   └── airsense.py         # Indoor IAQ + reports
│   └── admin/
│       └── admin_panel.py      # Tier config, revenue, metrics
├── tests/                      # 40 unit/integration tests
└── reports/                    # Generated eval reports, figures
```

---

## 🔐 Responsible Use

> **Atmosphere360 is a prototype screening/triage tool.** It is **not** an official warning system and does not replace CPCB/MPCB monitoring. All AI recommendations require **human-in-the-loop verification**. Synthetic data is clearly labeled. Outdoor AQI ≠ indoor air quality.

**Limitations:**
- Strong autoregression (yesterday's AQI is hard baseline)
- Uneven station coverage (clusters near highways/industry)
- Point measurements ≠ whole ward exposure
- 2023 holdout viewed during development

---

## 📜 Licence & Credits

| Component | Source | Licence |
|-----------|--------|---------|
| Air Quality | CPCB / MPCB CAAQMS | Government Open Data (NDSAP) |
| Weather | Open-Meteo (ERA5) | CC BY 4.0 |
| Spatial | OpenStreetMap | ODbL |
| Live Search/Shopping/News | SerpApi | SerpApi Terms |
| LLM | Groq (Llama 3.3) | Groq Terms |

**Built by Ratnesh Pathak** for **Beyond 9TO5 Buildathon — Mumbai Edition** (Nov 22, 2026)

Released under **MIT License** — see [`LICENSE`](LICENSE)

---

<p align="center">
  <img src="assets/banner.svg" alt="Atmosphere360" width="60%">
</p>

<p align="center">
  <b>One platform. Three modes. One connected journey.</b><br>
  Detect → Understand → Act → Equip → Monitor
</p>