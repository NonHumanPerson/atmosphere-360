# Atmosphere360 🌍
### AI-Powered Air Quality Intelligence & Health Action Platform

<p align="center">
  <img src="assets/banner.svg" alt="Atmosphere360 — Mumbai Air Quality & Health Action Platform" width="100%">
</p>

<p align="center">
  <img alt="Status" src="https://img.shields.io/badge/status-prototype-orange">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="Streamlit" src="https://img.shields.io/badge/app-Streamlit-ff4b4b">
  <img alt="Data" src="https://img.shields.io/badge/data-CPCB%20%2B%20Open--Meteo%20%2B%20SerpApi%20%2B%20Groq-1b7f8c">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
  <img alt="Buildathon" src="https://img.shields.io/badge/Built%20for-Beyond%209TO5%20Buildathon%202026-purple">
</p>

<p align="center">
  <a href="https://atmosphere360aweb.streamlit.app/"><b>🚀 Live Demo (v1)</b></a> |
  <a href="#-quick-start">Quick Start</a> |
  <a href="#-platform-overview">Platform Overview</a> |
  <a href="#-architecture">Architecture</a> |
  <a href="reports/EVALUATION.md">Evaluation Report</a>
</p>

---

## 🌫️ The Problem

Air pollution is more than an environmental metric. It is a public-health challenge that affects everyday decisions, institutional preparedness, and urban planning.

Yet, air-quality information is often fragmented across monitoring systems, weather services, public advisories, and local reporting channels.

**Atmosphere360** brings these signals together into an AI-powered air-quality and health-action prototype designed for citizens, municipal authorities, and organisations.

Its central workflow:

**Detect pollution → Understand risk → Recommend action → Find suitable products → Monitor improvement**

Built for **Beyond 9TO5 Buildathon — Mumbai Edition**, held at Paytm, Andheri, on November 22, 2026.

---

## 🎯 Platform Overview

Atmosphere360 brings three user experiences together through a shared intelligence engine.

| Mode | Intended Audience | Key Modules |
|---|---|---|
| 🏠 **Citizen** | General public | My Air, AirCare AI, PurifierMatch, CivicPulse |
| 🏛️ **Officer** | BMC / MPCB teams | Command Center, Expected Alerts, Team Deployment, Complaint Queue |
| 🏢 **Enterprise** | Schools, hospitals, offices | AirSense Monitor, Building Portfolio |

### Shared Intelligence Engine

- Historical air-quality data from CPCB.
- Live weather and forecast information from Open-Meteo.
- Live search, news, maps, and shopping information through SerpApi.
- LightGBM-based AQI forecasting.
- Composite priority scoring.
- Groq-powered AI recommendations and briefings.

---

## ✨ Key Features

| Feature | What it does |
|---|---|
| **My Air** | Displays AQI, PM2.5, PM10, historical comparisons, an Air Score, activity guidance, and a 48-hour forecast. |
| **AirCare AI** | Conversational air-quality assistance using live context, forecasts, news, and CPCB bulletins. |
| **PurifierMatch** | Calculates required Clean Air Delivery Rate (CADR), compares purifier options, estimates total cost of ownership, and retrieves live prices. |
| **CivicPulse** | Supports photo- and location-based pollution complaints, AI categorisation, reference IDs, and status tracking. |
| **Command Center** | Provides hotspot mapping, priority zones, AI-generated briefings, complaint queues, and pollution-source discovery. |
| **Expected Alerts** | Combines AQI forecasts, wind conditions, persistence, and complaints to generate alert categories. |
| **Team Deployment** | Supports team dispatch and tracks deployment progress from dispatch to verification. |
| **Route Planner** | Generates nearest-neighbour inspection routes using Haversine distance calculations. |
| **AirSense Monitor** | Supports building and room registration, manual indoor PM2.5 readings, I/O ratio visualisation, and reports. |
| **Building Portfolio** | Provides a cross-building view of indoor air-quality readings and monitoring status. |
| **Admin Panel** | Provides tier configuration, feature flags, rate limits, revenue analytics, and system metrics. |

---

## 🏗️ Architecture

```text
┌───────────────────────────────────────────────────────────────┐
│                     ATMOSPHERE360                              │
├───────────────────┬────────────────────┬──────────────────────┤
│  CITIZEN          │  OFFICER           │  ENTERPRISE          │
│                   │                    │                      │
│  • My Air         │  • Command Center  │  • AirSense Monitor  │
│  • AirCare AI     │  • Expected Alerts │  • Building Portfolio│
│  • PurifierMatch  │  • Team Deployment │  • Indoor IAQ        │
│  • CivicPulse     │  • Complaint Queue │  • Reports           │
└───────────────────┴────────────────────┴──────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────┐
│                  SHARED INTELLIGENCE ENGINE                   │
│                                                               │
│  • CPCB historical air-quality data                           │
│  • Open-Meteo weather and forecast data                       │
│  • LightGBM AQI forecasting                                    │
│  • Five-criteria priority scoring                             │
│  • Groq-powered AI recommendations                            │
└───────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────┐
│                       DATA LAYER                              │
│                                                               │
│  • SerpApi: Search, Maps, Shopping, News, Extract             │
│  • Open-Meteo: Forecast and Air Quality APIs                  │
│  • SQLite: Complaints, teams, deployments, buildings, tiers   │
└───────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technologies |
|---|---|
| Application | Python, Streamlit |
| Machine Learning | LightGBM, Gradient Boosting |
| AI / LLM | Groq, Llama 3.3 |
| Data Processing | Pandas, Parquet |
| Database | SQLite |
| Weather & Air Quality | Open-Meteo |
| Historical Air Quality | CPCB CAAQMS |
| Live Search & Discovery | SerpApi |
| Testing | Python unittest |

---

## 📋 Module Details

### 🏠 Citizen Mode

| Module | Capabilities |
|---|---|
| **My Air** | Live AQI, PM2.5, PM10, three-year baseline comparisons, Air Score (0–100), activity guidance, and 48-hour forecasts. |
| **AirCare** | Groq-powered chatbot with forecast, news, and CPCB context; supports home, office, school, and outdoor context selection. |
| **PurifierMatch** | CADR calculation, Budget/Balanced/Premium recommendations, product comparison, total cost of ownership, and live pricing. |
| **CivicPulse** | Photo and location-based complaint submission, AI categorisation, reference ID generation, and complaint status tracking. |

### 🏛️ Officer Mode

| Module | Capabilities |
|---|---|
| **Command Center** | City hotspot map, top-five priority zones, AI daily briefing, citizen complaint queue, and pollution-source discovery. |
| **Expected Alerts** | Uses AQI forecast, wind speed, persistence, and complaint signals to generate High Alert, Watch, or Advisory categories. |
| **Team Deployment** | Supports dispatch across BMC Ward A/B, MPCB, Traffic, and Fire teams, with deployment status tracking. |
| **Route Planner** | Uses Haversine distance and nearest-neighbour routing to create inspection itineraries for priority zones. |

### 🏢 Enterprise Mode

| Module | Capabilities |
|---|---|
| **AirSense Monitor** | Building and room registration, manual indoor PM2.5 readings, indoor/outdoor ratio charts, WHO guideline overlays, and Groq-generated PDF reports. |
| **Building Portfolio** | Aggregated building-level PM2.5 readings, monitoring coverage, and action status. |

### 🔧 Admin Panel

The owner-facing administration interface includes:

- Free, Pro, Enterprise, and Officer tier configuration.
- Feature flags and rate limits.
- Pricing and revenue analytics.
- Affiliate commission tracking.
- Complaint, deployment, team, alert, and building metrics.
- API connectivity checks.

---

## 📊 Data & Machine Learning

### Data Sources

| Dataset | Source | Coverage |
|---|---|---|
| Historical AQI | CPCB CAAQMS | 597,912 hourly records, 36 stations (30 active), 2021–2023 |
| Historical Weather | Open-Meteo ERA5 | 26,280 hourly observations, Mumbai coordinates |
| Live Forecast | Open-Meteo API | 48-hour hourly forecast, including temperature, humidity, wind, PM2.5, PM10, and AQI |
| Live Product Prices | SerpApi Shopping | INR pricing from supported shopping sources |
| Live News | SerpApi News | Pollution bulletins and policy announcements |
| Pollution Sources | SerpApi Maps | Nearby factories, construction, and traffic-related locations |

### Models & Evaluation

| Component | Approach | Reported Result |
|---|---|---|
| Next-day AQI Forecast | LightGBM L1 Residual | MAE: 18.83 vs 19.42 persistence baseline |
| Severe-day Detection | Gradient Boosting Classifier | Recall: 0.870, PR-AUC: 0.812 |
| Priority Scoring | Five-criteria composite | Exposure, persistence, forecast, trend, and monitoring gap |
| Prediction Intervals | 80% prediction intervals | 73.8% empirical coverage |
| Inspection Prioritisation | Weekly inspection backtest | 43% hit-rate lift over random selection |

### Priority Score

The composite score combines five criteria:

| Criterion | Weight |
|---|---:|
| Exposure | 30% |
| Persistence | 25% |
| Forecast | 20% |
| Trend | 15% |
| Monitoring Gap | 10% |

**Evaluation note:** The reported 2023 holdout results are exploratory because the holdout was viewed during development. They should not be interpreted as results from a fully independent, untouched test set. See the [Evaluation Report](reports/EVALUATION.md) for methodology and details.

---

## ⚡ Quick Start

### Prerequisites

- Python 3.10 or later.
- Git.
- SerpApi API key.
- Groq API key.

### 1. Clone the repository

```bash
git clone https://github.com/RatneshPathak/atmosphere360-2.0.git
cd atmosphere360-2.0
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Configure API keys

Create your environment file:

```bash
cp .env.example .env
```

Add your API credentials:

```env
SERPAPI_KEY=your_serpapi_key
GROQ_API_KEY=your_groq_api_key
```

Get API credentials:

- [SerpApi](https://serpapi.com/)
- [Groq Console](https://console.groq.com/keys)

**Security:** Never commit `.env` or expose API keys, administrator passwords, or other secrets in source code or public documentation.

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
streamlit run app.py
```

Open the application at:

```text
http://localhost:8501
```

### Admin Access

Select **Admin — Owner Panel** from the application mode selector.

Configure the administrator password securely through the application's supported environment or secrets configuration. Do not use a publicly documented default password.

---

## 🧪 Testing & Evaluation

Run the unit and integration test suite:

```bash
python -m unittest discover tests
```

Run the full evaluation:

```bash
pip install -r requirements-dev.txt
python Evaluate.py --full
```

Run the quicker evaluation:

```bash
python Evaluate.py --quick
```

The repository includes 40 unit and integration tests, alongside evaluation scripts for reproducing reported model metrics.

For additional methodology and results, see [`reports/EVALUATION.md`](reports/EVALUATION.md).

---

## 📁 Repository Structure

```text
atmosphere360-2.0/
│
├── app.py
├── config.py
├── serpapi_client.py
├── requirements.txt
├── requirements-dev.txt
├── .env.example
│
├── data/
│   ├── raw/
│   └── processed/
│
├── src/
│   ├── ingest/
│   │   └── live_feed.py
│   ├── llm/
│   │   └── groq_client.py
│   ├── utils/
│   │   └── cadr_calculator.py
│   ├── data/
│   │   └── sqlite_store.py
│   ├── citizen/
│   │   ├── my_air.py
│   │   ├── aircare.py
│   │   └── purifier_match.py
│   ├── officer/
│   │   ├── civic_pulse.py
│   │   └── command_center.py
│   ├── enterprise/
│   │   └── airsense.py
│   └── admin/
│       └── admin_panel.py
│
├── tests/
├── reports/
├── assets/
└── LICENSE
```

---

## 🔐 Responsible Use & Limitations

> **Atmosphere360 is a prototype screening and triage tool. It is not an official pollution-warning system and does not replace CPCB/MPCB monitoring or professional health advice. AI-generated recommendations require human verification.**

### Current Limitations

- Strong autoregressive behaviour: yesterday's AQI is a challenging baseline.
- Uneven monitoring-station distribution, with clusters near highways and industrial areas.
- Point measurements do not represent the exposure of an entire ward.
- The 2023 holdout was viewed during development, limiting claims of independent generalisation.
- Outdoor AQI does not directly represent indoor air quality.
- Indoor PM2.5 monitoring currently relies on manually entered readings.

Synthetic data, where used, should be treated as illustrative rather than observed measurements.

---

## 📜 Data Sources, Licences & Credits

| Component | Source | Licence / Terms |
|---|---|---|
| Air Quality | CPCB / MPCB CAAQMS | Government Open Data (NDSAP) |
| Weather | Open-Meteo ERA5 | CC BY 4.0 |
| Spatial Data | OpenStreetMap | ODbL |
| Live Search, Shopping & News | SerpApi | SerpApi Terms |
| LLM | Groq / Llama 3.3 | Applicable provider and model terms |

Please review the respective provider terms before using or redistributing source data.

---

## 👨‍💻 Author

**Ratnesh Pathak**

Built for **Beyond 9TO5 Buildathon — Mumbai Edition (2026)**.

- GitHub: [@RatneshPathak](https://github.com/RatneshPathak)
- Project Repository: [Atmosphere360](https://github.com/RatneshPathak/atmosphere360-2.0)
- Live Demo: [Atmosphere360 v1](https://atmosphere360aweb.streamlit.app/)

---

## 📄 Licence

Released under the MIT License. See [`LICENSE`](LICENSE) for details.

<p align="center">
  <img src="assets/banner.svg" alt="Atmosphere360" width="60%">
</p>

<p align="center">
  <b>One platform. Three modes. One connected journey.</b>
  <br>
  Detect → Understand → Act → Equip → Monitor
</p>
