# VayuMitra – Technical Project Documentation

## 1. Overview
**VayuMitra – Beyond Air Quality Monitoring** is an intelligent **Air Quality Monitoring, Investigation, Prediction, and Emergency Response Platform** built strictly with:
- **Frontend**: HTML5, CSS3, Vanilla JavaScript, **Chart.js** (analytics & trend graphs), and **Leaflet.js** (interactive route & hotspot maps).
- **Backend**: Python 3 + Flask (`backend/app.py`, `backend/services.py`, `backend/config.py`), plus a zero-dependency `--stdlib` HTTP server mode (`app.py --stdlib`) sharing the same backend service functions and REST API routes.
- **Database**: SQLite3 (`database/vayumitra.db`) with idempotent startup migrations in `init_db()`.

---

## 2. Folder Structure
```text
VayuMitra/
├── frontend/
│   ├── index.html          # Home – Intelligent Air Dashboard
│   ├── insights.html       # Insights – Pollution Intelligence Centre
│   ├── routes.html         # Routes – Smart Clean-Air Navigation
│   ├── alerts.html         # Alerts – Pollution Emergency System
│   ├── reports.html        # Reports – Environmental Intelligence Reports
│   ├── community.html      # Community – Air Guardian Network
│   ├── profile.html        # Profile – My Personal Air Twin & Settings
│   ├── css/
│   │   ├── style.css
│   │   ├── pages.css
│   │   └── responsive.css
│   ├── javascript/
│   │   ├── main.js
│   │   ├── api.js
│   │   └── features.js
│   └── assets/
│       ├── images/
│       ├── icons/
│       └── backgrounds/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── services.py
│   └── requirements.txt
├── database/
│   └── vayumitra.db
├── docs/
│   └── project_documentation.md
├── .gitignore
└── README.md
```

---

## 3. Data Integrity & Classification Standards
VayuMitra enforces clear separation between real environmental telemetry and analytical/citizen/hypothetical outputs:
- **Live / Measured**: Air quality (`pm2_5`, `pm10`, `nitrogen_dioxide`, `sulphur_dioxide`, `carbon_monoxide`, `ozone`, `us_aqi`, `european_aqi`) and weather (`temperature_2m`, `relative_humidity_2m`, `wind_speed_10m`) retrieved from Open-Meteo with explicit source attribution and timestamp. When live data cannot be retrieved, VayuMitra reports unavailable data honestly instead of fabricating readings.
- **Reported (Verified vs. Unverified)**: Citizen submissions stored locally in SQLite (`community_reports`), displaying local verification workflow statuses (`Submitted`, `Under Review`, `Verified`, `Resolved`, `Rejected`) without claiming official municipal/government dispatch.
- **Calculated**: Derived metrics such as Indian NAQI sub-indices, source ratio heuristics, baseline historical comparisons, clean-air windows, and Personal Air Twin exposure calculations.
- **Predicted**: Hourly and 3-day outlook forecasts (`past_days=3, forecast_days=3`) paired with explicit `confidence_low` / `confidence_high` bounds and data quality indicators.
- **Hypothetical / Simulated**: Scenario outputs from `POST /api/insights/simulate` (`is_hypothetical: true`), accompanied by explicit modeling assumptions.

### External Providers
- **Air Quality & Historical Archive**: Open-Meteo Air Quality API (zero-key default).
- **Weather Forecast**: Open-Meteo Weather API (zero-key default).
- **Geocoding**: Open-Meteo Geocoding API & OpenStreetMap Nominatim.
- **Routing**: OSRM (`router.project-osrm.org`) with AQI checkpoint sampling along decoded route geometry.

---

## 4. Separated AQI Standards & 6-Category Scale
VayuMitra never mixes AQI scales:
- **Indian NAQI (CPCB 0–500)**: Computed via `compute_indian_naqi()` from PM2.5, PM10, NO2, SO2, CO, and O3 sub-indices.
- **US EPA (0–500)**: Uses `us_aqi` mapped to the unified 6-level display taxonomy.
- **EU EAQI**: Uses `european_aqi` mapped to EU EAQI thresholds across the 6 semantic display labels.

Unified 6 semantic status labels (`classify_aqi(aqi_value, standard)`):
1. `Good`
2. `Satisfactory`
3. `Moderate`
4. `Poor`
5. `Very Poor`
6. `Severe`

---

## 5. SQLite Schema (`database/vayumitra.db`)
Managed automatically in `init_db()` (`backend/services.py`):
- `user_profiles`: Profile metadata and salted PBKDF2-HMAC-SHA256 password hashes.
- `user_preferences`: Default city, temperature unit (`C`/`F`), CO unit (`ugm3`/`mgm3`), AQI standard (`NAQI`/`US`/`EU`), and privacy controls.
- `notification_preferences`: Alert toggles, AQI & PM2.5 thresholds, and browser notification flags.
- `environmental_readings`: Persisted live snapshots (`aqi`, `pm25`, `pm10`, `no2`, `so2`, `co`, `o3`, weather) for Time Machine & Reporting.
- `environmental_alerts`: Threshold alert records.
- `community_reports` & `report_uploads`: Citizen reports across the 6 standardized categories plus validated upload metadata.
- `personal_locations`: Frequent Indian places with `hours_per_day` routine allocation.
- `personal_activities`: Outdoor/commute activities with duration and intensity weighting.
- `exposure_diary`: Logged Personal Air Twin daily exposure entries (`idx_diary_date`).
- `contact_messages`: Contact submissions.

---

## 6. REST API Endpoints

### Air Quality & Intelligence
- `GET /api/dashboard` – Live dashboard payload (`aqi_standard`, 6-level category, pollutants, weather, 24h trend, `is_live`).
- `GET /api/locations/india` – Pan-India city & state autocomplete dataset.
- `GET /api/air-quality` – Current AQI & pollutant breakdown by `city` or `lat`/`lon`.
- `GET /api/air-quality/forecast` – Hourly & 3-day outlook (`daily_forecast`, `forecast_period`, `historical_basis_note`, uncertainty bounds).
- `GET /api/air-quality/history` – Persisted SQLite readings.
- `GET /api/insights` – Live conditions, 3-day outlook, **Best Outdoor Windows** (`clean_air_windows`), diurnal pattern, and **Likely Pollution Sources** with `historical_comparison`.
- `POST /api/insights/simulate` – Hypothetical What-If simulator supporting `traffic_reduction_pct`, `industrial_reduction_pct`, `dust_control_pct`, `burning_reduction_pct`, and `greenery_increase_pct`, returning `assumptions`, `impact_explanation`, and `comparison_chart_series`.

### Navigation, Alerts & Reports
- `GET /api/routes` – 2-way route comparison (`Ordinary Route` vs. `Safe Air Route`) with `duration_min`, `distance_km`, `hotspot_zones`, `incident_updates`, `emergency_escape`, and `clean_air_windows`.
- `GET /api/alerts` – Threshold alerts, 6-level warning guide, Emergency Escape link context, and `hotspot_updates` (`Verified` vs. `Reported`).
- `GET /api/reports` – Period (`daily`/`weekly`/`monthly`/`custom` + `start_date`/`end_date`) environmental report with `generated_at` and optional side-by-side `compare_city` comparison payload.
- `GET /api/reports/export` – CSV report download.

### Community & Air Guardian Network
- `GET /api/community/reports` – Filterable citizen reports (`status`, `category`, `search`) across the 6 standard categories (with legacy category compatibility mapping).
- `POST /api/community/report` – Submit report (multipart form or JSON) with optional photo (`<= 5 MB`).
- `PUT /api/community/reports/<id>/status` – Update verification/resolution status in local SQLite.
- `GET /api/uploads/<filename>` – Safe uploaded file serving.

### Personal Air Twin & Settings
- `GET /api/air-twin` – Frequent locations (`hours_per_day`), `location_comparison`, `weekly_exposure_trend`, activities, and `exposure_diary`.
- `POST /api/air-twin/locations` & `DELETE /api/air-twin/locations/<id>`
- `POST /api/air-twin/activities` & `DELETE /api/air-twin/activities/<id>`
- `POST /api/air-twin/diary` – Record a daily exposure diary entry.
- `GET /api/air-twin/export` – Export Personal Air Twin & diary CSV.
- `GET /api/profile` & `PUT /api/profile` – Profile, AQI standard (`NAQI`/`US`/`EU`), units, notification thresholds, and password updates.
- `POST /api/contact` – Contact submission.

---

## 7. Local Execution (VS Code / Terminal)
- **Flask mode (recommended)**:
  ```powershell
  cd VayuMitra
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  pip install -r backend\requirements.txt
  python backend\app.py
  ```
- **Standard-library fallback mode** (no external packages needed):
  ```bash
  python backend/app.py --stdlib --host 127.0.0.1 --port 5000
  ```
