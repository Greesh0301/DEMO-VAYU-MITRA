/* VayuMitra Page-Specific Feature Controllers */
(function (window, document) {
  "use strict";

  const chartRegistry = {};

  function renderOrReplaceChart(canvasId, config) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof window.Chart === "undefined") return null;
    if (chartRegistry[canvasId]) {
      chartRegistry[canvasId].destroy();
    }
    const ctx = canvas.getContext("2d");
    chartRegistry[canvasId] = new window.Chart(ctx, config);
    return chartRegistry[canvasId];
  }

  function levelBadgeClass(levelOrCategory) {
    const key = String(levelOrCategory || "").toLowerCase();
    if (key.includes("good")) return "vm-status-good";
    if (key.includes("satisfactory")) return "vm-status-satisfactory";
    if (key.includes("moderate")) return "vm-status-moderate";
    if (key.includes("severe") || key.includes("hazard")) return "vm-status-severe";
    if (key.includes("very poor") || key.includes("worse")) return "vm-status-worse";
    if (key.includes("poor") || key.includes("bad") || key.includes("unhealthy")) return "vm-status-bad";
    return "vm-status-moderate";
  }

  function aqiColorHex(aqi) {
    if (aqi == null || Number.isNaN(Number(aqi))) return "#64748B";
    if (aqi <= 50) return "#16A34A";
    if (aqi <= 100) return "#059669";
    if (aqi <= 200) return "#D97706";
    if (aqi <= 300) return "#EA580C";
    if (aqi <= 400) return "#DC2626";
    return "#7F1D1D";
  }

  function naqiCategoryFromValue(aqi) {
    if (aqi == null || Number.isNaN(Number(aqi))) return "Unavailable";
    if (aqi <= 50) return "Good";
    if (aqi <= 100) return "Satisfactory";
    if (aqi <= 200) return "Moderate";
    if (aqi <= 300) return "Poor";
    if (aqi <= 400) return "Very Poor";
    return "Severe";
  }

  function renderAqiGaugeSvg(containerId, aqiValue, labelSub, categoryText) {
    const el = document.getElementById(containerId);
    if (!el) return;
    const hasNum = aqiValue != null && !Number.isNaN(Number(aqiValue));
    const num = hasNum ? Math.round(Number(aqiValue)) : null;
    const pct = hasNum ? Math.max(0.03, Math.min(1, num / 400)) : 0;
    const arcLen = 251.33;
    const offset = arcLen * (1 - pct);
    const color = hasNum ? aqiColorHex(num) : "#64748B";
    const catLabel = categoryText || (hasNum ? naqiCategoryFromValue(num) : "Unavailable");
    const catCls = levelBadgeClass(catLabel);

    el.innerHTML = `
      <svg class="vm-gauge-svg" viewBox="0 0 200 118" role="img" aria-label="AQI ${num != null ? num : "--"} ${window.VayuMain.escapeHtml(catLabel)}">
        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="rgba(16,52,59,0.10)" stroke-width="16" stroke-linecap="round"></path>
        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="${color}" stroke-width="16" stroke-linecap="round"
          stroke-dasharray="${arcLen}" stroke-dashoffset="${offset.toFixed(1)}" style="transition:stroke-dashoffset 450ms ease, stroke 300ms ease;"></path>
      </svg>
      <div class="vm-gauge-center">
        <div class="vm-gauge-num" style="color:${color};">${num != null ? num : "--"}</div>
        <div class="vm-gauge-sub">${window.VayuMain.escapeHtml(labelSub || "AQI")}</div>
        <span class="vm-status-tag ${catCls}" style="margin-top:4px;">${window.VayuMain.escapeHtml(catLabel)}</span>
      </div>
    `;
  }

  /* =========================================================
     1. DASHBOARD (index.html)
     ========================================================= */
  async function initDashboardPage() {
    const greetingEl = document.getElementById("vmTimeGreeting");
    if (greetingEl) {
      greetingEl.textContent = window.VayuMain.getTimeGreeting();
    }

    const dateEl = document.getElementById("vmHeroDate");
    if (dateEl) {
      dateEl.textContent = window.VayuMain.formatFullDate(new Date());
    }

    const geoBtn = document.getElementById("vmUseLocationBtn");

    async function loadDashboard(params, isInitial) {
      window.VayuMain.showBanner("vmDashboardBanner", "", "info");
      try {
        const data = await window.VayuApi.getDashboard(params);
        window.VayuMain.updateHeaderWeather(data);
        renderDashboardData(data);
      } catch (err) {
        if (isInitial && (params.city || params.lat != null)) {
          window.VayuMain.clearStoredLocation();
          window.VayuMain.updateCityBackground("Mumbai");
          try {
            const fallback = await window.VayuApi.getDashboard({ city: "Mumbai" });
            window.VayuMain.updateHeaderWeather(fallback);
            renderDashboardData(fallback);
            window.VayuMain.showBanner("vmDashboardBanner", "VayuMitra supports locations within India only. Reset view to Mumbai.", "info");
            return;
          } catch (_fallbackErr) {}
        }
        window.VayuMain.showBanner("vmDashboardBanner", err.message || "Unable to fetch live air quality data.", "error");
      }
    }

    window.addEventListener("vayumitra:citychange", (ev) => {
      const city = ev.detail && ev.detail.city;
      if (city) loadDashboard({ city }, false);
    });

    if (geoBtn) {
      geoBtn.addEventListener("click", async () => {
        geoBtn.disabled = true;
        geoBtn.textContent = "Detecting...";
        try {
          const coords = await window.VayuMain.requestBrowserLocation();
          await loadDashboard({ lat: coords.lat, lon: coords.lon }, false);
          window.VayuMain.setStoredCoords(coords.lat, coords.lon);
        } catch (err) {
          window.VayuMain.showBanner("vmDashboardBanner", err.message, "error");
        } finally {
          geoBtn.disabled = false;
          geoBtn.textContent = "Use my location";
        }
      });
    }

    const initialParams = window.VayuMain.getStoredLocationParams();
    await loadDashboard(initialParams, true);
  }

  function renderDashboardData(data) {
    const cls = data.classification || {};
    const level = cls.level || "good";
    const loc = data.location || {};
    const weather = data.weather || {};
    const pollutants = data.pollutants || {};
    const unitMode = data.pollutant_unit_mode || "ugm3";

    const heroLoc = document.getElementById("vmHeroLocation");
    if (heroLoc) {
      const region = [loc.name, loc.admin1, loc.country].filter(Boolean).join(", ");
      heroLoc.textContent = region || loc.name || "Mumbai";
    }

    const mainCard = document.getElementById("vmMainAqiCard");
    if (mainCard) {
      mainCard.classList.remove(
        "aqi-level-good",
        "aqi-level-satisfactory",
        "aqi-level-moderate",
        "aqi-level-bad",
        "aqi-level-worse",
        "aqi-level-severe"
      );
      mainCard.classList.add(`aqi-level-${level}`);
    }

    const aqiBadge = document.getElementById("vmAqiBadge");
    if (aqiBadge) {
      aqiBadge.className = `vm-status-tag ${levelBadgeClass(cls.category)}`;
      aqiBadge.textContent = `${cls.category || "Unknown"} Air Quality`;
    }

    setText("vmDataOriginBadge", data.is_live ? "Live Feed" : "Estimated");
    setText("vmAqiStandard", `${data.aqi_standard || "NAQI"} Standard`);
    setText("vmCardWeatherCond", weather.condition || "Clear");
    setText(
      "vmHeroWeatherTemp",
      weather.temperature != null ? `${weather.temperature.toFixed(1)} ${weather.temp_unit || "°C"}` : "--"
    );

    renderAqiGaugeSvg("vmMainAqiGauge", data.aqi, data.aqi_standard || "NAQI", cls.category);

    setText("vmCardLocation", loc.name || "Unknown");
    setText("vmTrendCityLabel", loc.name || "your city");
    setText("vmCardUpdated", window.VayuMain.formatDateTime(data.recorded_at));
    setText("vmCardSource", data.source || "Open-Meteo Air Quality");
    setText("vmAqiMessage", cls.message || "");

    const charImg = document.getElementById("vmAqiCharacterImg");
    if (charImg) {
      charImg.src = cls.illustration || "assets/images/aqi-good.svg";
      charImg.alt = `Girl and boy reacting to ${cls.category || "current"} air quality`;
    }
    setText(
      "vmAqiCharacterCaption",
      `${cls.category || "Good"} · ${cls.recommendation || cls.message || "Fresh air conditions."}`
    );

    setStat("statTempVal", weather.temperature != null ? weather.temperature.toFixed(1) : "N/A", weather.temp_unit || "°C");
    setStat("statHumVal", weather.humidity != null ? Math.round(weather.humidity) : "N/A", "%");
    setStat("statWindVal", weather.wind_speed != null ? weather.wind_speed.toFixed(1) : "N/A", "km/h");

    const pollutantSpecs = [
      { id: "pm2_5", label: "PM2.5", max: 150, val: pollutants.pm2_5 },
      { id: "pm10", label: "PM10", max: 250, val: pollutants.pm10 },
      { id: "no2", label: "NO₂", max: 200, val: pollutants.no2 },
      { id: "co", label: "CO", max: 4000, val: pollutants.co },
      { id: "o3", label: "O₃", max: 180, val: pollutants.o3 },
      { id: "so2", label: "SO₂", max: 200, val: pollutants.so2 },
    ];

    const barsEl = document.getElementById("vmHomePollutantBars");
    if (barsEl) {
      barsEl.innerHTML = pollutantSpecs
        .map((p) => {
          const fmt = window.VayuMain.formatPollutant(p.val, p.id, unitMode);
          const pct = p.val != null ? Math.min(100, Math.max(5, Math.round((p.val / p.max) * 100))) : 0;
          const barColor = pct >= 70 ? "#DC2626" : pct >= 45 ? "#EA580C" : pct >= 25 ? "#D97706" : "#16A34A";
          return `
            <div class="vm-pbar-row">
              <span class="vm-pbar-name">${p.label}</span>
              <div class="vm-pbar-track">
                <div class="vm-pbar-fill" style="width:${pct}%; background:${barColor};"></div>
              </div>
              <span class="vm-pbar-val">${window.VayuMain.escapeHtml(fmt.text)} ${window.VayuMain.escapeHtml(fmt.unit)}</span>
            </div>
          `;
        })
        .join("");
    }

    const precList = document.getElementById("vmHomePrecautionsList");
    if (precList) {
      const precs = Array.isArray(cls.precautions) && cls.precautions.length
        ? cls.precautions
        : [cls.message, cls.recommendation].filter(Boolean);
      precList.innerHTML = precs.length
        ? precs
            .slice(0, 4)
            .map(
              (item) => `
              <li>
                <span class="vm-check-ico">&check;</span>
                <span>${window.VayuMain.escapeHtml(item)}</span>
              </li>
            `
            )
            .join("")
        : `<li><span class="vm-check-ico">&check;</span><span>Monitor air quality before outdoor exercise.</span></li>`;
    }

    const history = data.hourly_history || [];
    const trendEmpty = document.getElementById("vmTrendEmpty");
    if (history.length > 0) {
      if (trendEmpty) trendEmpty.classList.add("vm-hidden");
      renderOrReplaceChart("vmDashboardTrendChart", {
        type: "line",
        data: {
          labels: history.map((h) => window.VayuMain.formatHourLabel(h.time)),
          datasets: [
            {
              label: "Hourly AQI",
              data: history.map((h) => h.aqi),
              borderColor: "#1b8a4b",
              backgroundColor: "rgba(27, 138, 75, 0.14)",
              fill: true,
              tension: 0.35,
              pointRadius: 3,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, title: { display: true, text: "AQI" } } },
        },
      });
    } else if (trendEmpty) {
      trendEmpty.classList.remove("vm-hidden");
    }

    const alerts = data.active_alerts || [];
    const alertCard = document.getElementById("vmHomeAlertStatusCard");
    const alertBadge = document.getElementById("vmHomeAlertBadge");
    if (alertCard) {
      const hasAlert = alerts.length > 0 || (data.aqi != null && data.aqi > 150);
      alertCard.classList.toggle("is-warning", hasAlert);
      if (alerts.length > 0) {
        const top = alerts[0];
        setText("vmHomeAlertTitle", top.alert_title || "Active Pollution Alert");
        setText("vmHomeAlertDesc", top.description || `AQI in ${loc.name || "your area"} requires precautions.`);
        if (alertBadge) {
          alertBadge.className = `vm-status-tag ${levelBadgeClass(top.alert_level)}`;
          alertBadge.textContent = `${alerts.length} Active`;
        }
      } else {
        setText("vmHomeAlertTitle", "No Alerts");
        setText("vmHomeAlertDesc", `Air quality is ${String(cls.category || "satisfactory").toLowerCase()} in ${loc.name || "your area"}.`);
        if (alertBadge) {
          alertBadge.className = "vm-status-tag vm-status-good";
          alertBadge.textContent = "OK";
        }
      }
    }
  }

  function setStat(id, value, unit) {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = `${window.VayuMain.escapeHtml(String(value))} <span class="vm-stat-unit">${window.VayuMain.escapeHtml(unit || "")}</span>`;
  }

  /* =========================================================
     2. POLLUTION INTELLIGENCE CENTRE (insights.html)
     ========================================================= */
  async function initInsightsPage() {
    let currentParams = window.VayuMain.getStoredLocationParams();

    document.querySelectorAll(".vm-jump-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        document.querySelectorAll(".vm-jump-pill").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
      });
    });

    async function loadTimeMachine(params, targetDate) {
      const tmSel = document.getElementById("tmTargetDate");
      if (!tmSel && !document.getElementById("vmTimeMachineBarChart")) return;
      try {
        const tm = await window.VayuApi.getTimeMachine(
          Object.assign({}, params || currentParams, targetDate ? { target_date: targetDate } : {})
        );
        const dates = (tm.available_dates || []).slice().reverse();
        if (tmSel && dates.length) {
          tmSel.innerHTML = dates
            .map((d) => `<option value="${window.VayuMain.escapeHtml(d)}" ${d === tm.target_date ? "selected" : ""}>${window.VayuMain.escapeHtml(d)}</option>`)
            .join("");
        }
        const series = tm.target_series || [];
        if (series.length) {
          renderOrReplaceChart("vmTimeMachineBarChart", {
            type: "bar",
            data: {
              labels: series.map((pt) => window.VayuMain.formatHourLabel(pt.time || `2000-01-01T${pt.hour}`)),
              datasets: [
                {
                  label: `Hourly AQI (${tm.target_date || ""})`,
                  data: series.map((pt) => pt.aqi),
                  backgroundColor: series.map((pt) => aqiColorHex(pt.aqi)),
                  borderRadius: 6,
                  barPercentage: 0.72,
                },
              ],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { display: false } },
              scales: {
                y: { beginAtZero: true, title: { display: true, text: "AQI" } },
                x: { ticks: { maxTicksLimit: 8 } },
              },
            },
          });
        }
      } catch (_tmErr) {}
    }

    async function loadInsights(params, isInitial) {
      currentParams = params;
      window.VayuMain.showBanner("vmInsightsBanner", "", "info");
      try {
        const data = await window.VayuApi.getInsights(params);
        window.VayuMain.updateHeaderWeather(data.current);
        renderInsights(data);
        await Promise.all([runSimulation(params), loadTimeMachine(params)]);
      } catch (err) {
        if (isInitial && (params.city || params.lat != null)) {
          window.VayuMain.clearStoredLocation();
          window.VayuMain.updateCityBackground("Mumbai");
          try {
            const fallback = await window.VayuApi.getInsights({ city: "Mumbai" });
            currentParams = { city: "Mumbai" };
            window.VayuMain.updateHeaderWeather(fallback.current);
            renderInsights(fallback);
            await Promise.all([runSimulation(currentParams), loadTimeMachine(currentParams)]);
            window.VayuMain.showBanner("vmInsightsBanner", "VayuMitra supports locations within India only. Showing Mumbai.", "info");
            return;
          } catch (_e) {}
        }
        window.VayuMain.showBanner("vmInsightsBanner", err.message || "Forecast data unavailable.", "error");
      }
    }

    async function runSimulation(params) {
      const tVal = Number((document.getElementById("simTrafficSlider") || {}).value || 0);
      const dVal = Number((document.getElementById("simDustSlider") || {}).value || 0);
      const iVal = Number((document.getElementById("simIndustrialSlider") || {}).value || 0);
      const gVal = Number((document.getElementById("simGreenerySlider") || {}).value || 0);
      const bVal = Number((document.getElementById("simBurningSlider") || {}).value || 0);

      try {
        const payload = Object.assign({}, params || currentParams, {
          traffic_reduction_pct: tVal,
          dust_control_pct: dVal,
          industrial_reduction_pct: iVal,
          greenery_increase_pct: gVal,
          burning_reduction_pct: bVal,
        });
        const sim = await window.VayuApi.simulateWhatIf(payload);
        setText("simBaseAqi", `${sim.baseline.aqi} (${sim.baseline.category})`);
        setText("simOutAqi", `${sim.simulated.aqi} (${sim.simulated.category})`);
        setText("simOutPm25", `${sim.simulated.pm2_5} µg/m³`);
        setText("simOutNo2", `SO2 ${sim.simulated.so2} · NO2 ${sim.simulated.no2} µg/m³`);
        setText(
          "simResultSummary",
          `Hypothetical delta: ${sim.simulated.aqi_delta >= 0 ? "+" : ""}${sim.simulated.aqi_delta} AQI (${sim.simulated.pct_change}%)`
        );
        setText("simImpactExplanation", sim.impact_explanation || "");
        const assEl = document.getElementById("simAssumptionsList");
        if (assEl) {
          assEl.innerHTML = (sim.assumptions || []).map((a) => `<li>${window.VayuMain.escapeHtml(a)}</li>`).join("");
        }
        const cs = sim.comparison_chart_series;
        if (cs && cs.labels) {
          renderOrReplaceChart("vmSimulatorCompareChart", {
            type: "bar",
            data: {
              labels: cs.labels,
              datasets: [
                {
                  label: "Current Baseline",
                  data: cs.baseline,
                  backgroundColor: "rgba(16, 52, 59, 0.72)",
                  borderRadius: 6,
                },
                {
                  label: "Simulated Outcome",
                  data: cs.simulated,
                  backgroundColor: "rgba(27, 138, 75, 0.78)",
                  borderRadius: 6,
                },
              ],
            },
            options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } },
          });
        }
      } catch (_err) {}
    }

    const tmDateSel = document.getElementById("tmTargetDate");
    if (tmDateSel) {
      tmDateSel.addEventListener("change", () => {
        if (tmDateSel.value) loadTimeMachine(currentParams, tmDateSel.value);
      });
    }

    [
      ["simTrafficSlider", "simTrafficVal", "Control"],
      ["simDustSlider", "simDustVal", "Control"],
      ["simIndustrialSlider", "simIndustrialVal", "Control"],
      ["simGreenerySlider", "simGreeneryVal", "Boost"],
      ["simBurningSlider", "simBurningVal", "Control"],
    ].forEach(([sId, vId, verb]) => {
      const sl = document.getElementById(sId);
      if (sl) {
        setText(vId, `${verb} ${sl.value}%`);
        sl.addEventListener("input", () => {
          setText(vId, `${verb} ${sl.value}%`);
        });
      }
    });

    const simRunBtn = document.getElementById("simRunBtn");
    if (simRunBtn) {
      simRunBtn.addEventListener("click", () => runSimulation(currentParams));
    }
    const simResetBtn = document.getElementById("simResetBtn");
    if (simResetBtn) {
      simResetBtn.addEventListener("click", () => {
        ["simTrafficSlider", "simDustSlider", "simIndustrialSlider", "simGreenerySlider", "simBurningSlider"].forEach((id) => {
          const el = document.getElementById(id);
          if (el) el.value = "0";
        });
        setText("simTrafficVal", "Control 0%");
        setText("simDustVal", "Control 0%");
        setText("simIndustrialVal", "Control 0%");
        setText("simGreeneryVal", "Boost 0%");
        setText("simBurningVal", "Control 0%");
        runSimulation(currentParams);
      });
    }

    window.addEventListener("vayumitra:citychange", (ev) => {
      const city = ev.detail && ev.detail.city;
      if (city) loadInsights({ city }, false);
    });

    await loadInsights(currentParams, true);
  }

  function renderInsights(data) {
    const cur = data.current || {};
    const fcObj = data.forecast || {};
    const fc = fcObj.forecast_24h || [];
    const hist = fcObj.recent_history || [];
    const rate = data.rate_analysis || {};
    const pat = data.pattern_analysis || {};
    const fp = data.source_fingerprinting || {};

    setText("insLocationName", cur.location ? cur.location.name : "—");
    setText("insCurrentAqi", cur.aqi != null ? `${cur.aqi} (${cur.classification.category})` : "—");
    setText("insPm25", cur.pollutants && cur.pollutants.pm2_5 != null ? `${cur.pollutants.pm2_5.toFixed(1)} µg/m³` : "N/A");
    setText("insPm10", cur.pollutants && cur.pollutants.pm10 != null ? `${cur.pollutants.pm10.toFixed(1)} µg/m³` : "N/A");

    const candidates = fp.candidates || [];
    const dq = fcObj.data_quality || {};
    const topStrength = candidates.length ? Number(candidates[0].signal_strength || 60) : 55;
    const completeness = Number(dq.completeness_pct || 80);
    const confPct = Math.min(95, Math.max(45, Math.round(topStrength * 0.55 + completeness * 0.4)));
    setText("insFingerprintConfBadge", `Confidence Level: ${confPct}%`);

    const fpGrid = document.getElementById("insFingerprintGrid");
    if (fpGrid) {
      const buckets = { traffic: 0, dust: 0, industrial: 0, others: 0 };
      const evidences = { traffic: [], dust: [], industrial: [], others: [] };
      candidates.forEach((c) => {
        const name = String(c.source_name || "").toLowerCase();
        const val = Math.max(0, Number(c.signal_strength || 0));
        const ev = (c.evidence || []).join(" · ");
        if (name.includes("traffic") || name.includes("vehic")) {
          buckets.traffic += val;
          if (ev) evidences.traffic.push(ev);
        } else if (name.includes("construction") || name.includes("dust") || name.includes("soil")) {
          buckets.dust += val;
          if (ev) evidences.dust.push(ev);
        } else if (name.includes("industrial")) {
          buckets.industrial += val;
          if (ev) evidences.industrial.push(ev);
        } else {
          buckets.others += val;
          if (ev) evidences.others.push(ev);
        }
      });

      const rawSum = buckets.traffic + buckets.dust + buckets.industrial + buckets.others;
      let pctTraffic = 0;
      let pctDust = 0;
      let pctInd = 0;
      let pctOthers = 0;
      if (rawSum > 0) {
        pctTraffic = Math.round((buckets.traffic / rawSum) * 100);
        pctDust = Math.round((buckets.dust / rawSum) * 100);
        pctInd = Math.round((buckets.industrial / rawSum) * 100);
        pctOthers = Math.max(0, 100 - (pctTraffic + pctDust + pctInd));
      }

      const fpRows = [
        {
          label: "Traffic Emissions",
          pct: pctTraffic,
          color: "#16a34a",
          evidence: evidences.traffic.join(" | ") || "Derived from live NO₂ and CO vehicle emission ratios.",
          icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1e293b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"></path><circle cx="7" cy="17" r="2" fill="#1e293b"></circle><path d="M9 17h6"></path><circle cx="17" cy="17" r="2" fill="#1e293b"></circle></svg>`,
        },
        {
          label: "Construction Dust",
          pct: pctDust,
          color: "#f59e0b",
          evidence: evidences.dust.join(" | ") || "Derived from live PM10 coarse particulate and dust load.",
          icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 18a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v2z" fill="#fbbf24"></path><path d="M10 10V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v5"></path><path d="M4 15v-3a6 6 0 0 1 6-6h0"></path><path d="M14 6h0a6 6 0 0 1 6 6v3"></path></svg>`,
        },
        {
          label: "Industrial Activity",
          pct: pctInd,
          color: "#22a6e0",
          evidence: evidences.industrial.join(" | ") || "Derived from live SO₂ and combustion plume indicators.",
          icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#334155" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z" fill="#475569"></path><path d="M17 18h1" stroke="#fff"></path><path d="M12 18h1" stroke="#fff"></path><path d="M7 18h1" stroke="#fff"></path></svg>`,
        },
        {
          label: "Others",
          pct: pctOthers,
          color: "#b8c2cc",
          evidence: evidences.others.join(" | ") || "Includes biomass smoke, domestic burning, and atmospheric dispersion.",
          icon: `<svg width="22" height="22" viewBox="0 0 24 24" fill="#ef4444" stroke="#dc2626" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"></path></svg>`,
        },
      ];

      fpGrid.innerHTML = fpRows
        .map(
          (row) => `
          <div class="vm-fp-row" title="${window.VayuMain.escapeHtml(row.evidence)}">
            <span class="vm-fp-ico" aria-hidden="true">${row.icon}</span>
            <span class="vm-fp-label">${row.label}</span>
            <div class="vm-fp-track">
              <div class="vm-fp-fill" style="width:${row.pct}%; background:${row.color};"></div>
            </div>
            <span class="vm-fp-pct">${row.pct}%</span>
          </div>
        `
        )
        .join("");
    }

    const cmpBody = document.getElementById("insSourceCompareBody");
    if (cmpBody) {
      const rows = fp.historical_comparison || [];
      cmpBody.innerHTML = rows.length
        ? rows
            .map((r) => {
              const deltaText = r.delta_pct != null ? `${r.delta_pct >= 0 ? "+" : ""}${r.delta_pct}%` : "—";
              const sigCls =
                r.status === "Above Average"
                  ? "vm-status-bad"
                  : r.status === "Below Average"
                  ? "vm-status-good"
                  : "vm-status-satisfactory";
              return `
                <tr>
                  <td><strong>${window.VayuMain.escapeHtml(r.pollutant)}</strong></td>
                  <td class="tabular-nums">${r.current != null ? `${r.current} ${r.unit}` : "N/A"}</td>
                  <td class="tabular-nums">${r.avg_24h != null ? `${r.avg_24h} ${r.unit}` : "N/A"}</td>
                  <td class="tabular-nums">${r.avg_multiday != null ? `${r.avg_multiday} ${r.unit}` : "N/A"}</td>
                  <td class="tabular-nums">${window.VayuMain.escapeHtml(deltaText)}</td>
                  <td><span class="vm-status-tag ${sigCls}">${window.VayuMain.escapeHtml(r.status)}</span></td>
                </tr>
              `;
            })
            .join("")
        : `<tr><td colspan="6">Historical baseline comparison unavailable.</td></tr>`;
    }

    setText("insRateStatus", rate.status || "Unavailable");
    setText("insRateSummary", rate.summary || "");
    setText("insForecastQuality", dq.quality_badge ? `${dq.quality_badge} (${dq.completeness_pct}% 24h coverage)` : "Regional Grid");
    setText("insForecastPeriod", fcObj.forecast_period || "Next 24h & 3-Day Outlook");

    const expPt = pat.peak_forecast || (fc.length ? fc[0] : null);
    setText("insExpectedAqiVal", expPt && expPt.aqi != null ? String(expPt.aqi) : "--");
    const expBadge = document.getElementById("insExpectedAqiBadge");
    if (expBadge) {
      const cat = (expPt && expPt.category) || naqiCategoryFromValue(expPt ? expPt.aqi : null);
      expBadge.className = `vm-status-tag ${levelBadgeClass(cat)}`;
      expBadge.textContent = cat;
    }

    const dailyGrid = document.getElementById("insDailyForecastGrid");
    if (dailyGrid) {
      const dList = fcObj.daily_forecast || [];
      dailyGrid.innerHTML = dList
        .map(
          (d) => `
          <div class="vm-twin-item-row">
            <div>
              <strong class="font-mono">${window.VayuMain.escapeHtml(d.date)}</strong>
              <div class="vm-meta-line">Range: ${d.min_aqi}–${d.max_aqi} AQI (${d.hours}h)</div>
            </div>
            <span class="vm-status-tag ${levelBadgeClass(d.category)}">Avg ${d.avg_aqi} · ${window.VayuMain.escapeHtml(d.category)}</span>
          </div>
        `
        )
        .join("");
    }

    const insWinGrid = document.getElementById("vmInsightsWindowsGrid");
    if (insWinGrid) {
      const windows = data.clean_air_windows || [];
      insWinGrid.innerHTML = windows.length
        ? windows
            .map((w) => {
              const stCls = w.status === "Avoid" ? "vm-status-worse" : w.status === "Caution" ? "vm-status-moderate" : "vm-status-good";
              return `
                <article class="vm-card">
                  <div class="vm-aqi-header-row" style="margin-bottom:6px;">
                    <span class="vm-stat-label">${window.VayuMain.escapeHtml(w.label)}</span>
                    <span class="vm-status-tag ${stCls}">${window.VayuMain.escapeHtml(w.status)}</span>
                  </div>
                  <div class="vm-stat-value tabular-nums" style="font-size:1.25rem;">${window.VayuMain.formatHourLabel(w.time)} · AQI ${w.aqi}</div>
                  <div class="vm-meta-line" style="margin-top:4px;">${window.VayuMain.escapeHtml(w.expected_change || w.category)}</div>
                  <p class="vm-section-subtitle" style="margin-top:6px;">${window.VayuMain.escapeHtml(w.guidance)}</p>
                  ${w.precaution ? `<p class="vm-meta-line" style="margin-top:6px;"><strong>Precaution:</strong> ${window.VayuMain.escapeHtml(w.precaution)}</p>` : ""}
                </article>
              `;
            })
            .join("")
        : `<article class="vm-card">24-hour clean-air window predictions unavailable right now.</article>`;
    }

    setText(
      "insPeakWindow",
      pat.peak_forecast
        ? `${window.VayuMain.formatHourLabel(pat.peak_forecast.time)} · AQI ${pat.peak_forecast.aqi} (${pat.peak_forecast.confidence_low}–${pat.peak_forecast.confidence_high})`
        : "Unavailable"
    );
    setText(
      "insCleanWindow",
      pat.cleanest_forecast ? `${window.VayuMain.formatHourLabel(pat.cleanest_forecast.time)} · AQI ${pat.cleanest_forecast.aqi}` : "Unavailable"
    );
    setText(
      "insDayNightAvg",
      pat.daytime_avg_aqi != null && pat.nighttime_avg_aqi != null
        ? `Day ${pat.daytime_avg_aqi} · Night ${pat.nighttime_avg_aqi}`
        : "Insufficient history"
    );

    const obsEl = document.getElementById("insObservationsList");
    if (obsEl) {
      const obs = pat.observations || [];
      obsEl.innerHTML = obs.length
        ? obs.map((o) => `<li>${window.VayuMain.escapeHtml(o)}</li>`).join("")
        : "<li>No pattern observations available for this location yet.</li>";
    }

    if (!fcObj.available || fc.length === 0) {
      window.VayuMain.showBanner("vmInsightsBanner", "24-hour forecast data is currently unavailable from the upstream provider.", "info");
      return;
    }

    const recentSlice = hist.slice(-12);
    const labels = [
      ...recentSlice.map((p) => `${window.VayuMain.formatHourLabel(p.time)}`),
      ...fc.map((p) => `${window.VayuMain.formatHourLabel(p.time)} (Pred)`),
    ];
    const histSeries = [...recentSlice.map((p) => p.aqi), ...fc.map(() => null)];
    const fcSeries = [...recentSlice.map((_, i) => (i === recentSlice.length - 1 ? pAqi(recentSlice[i]) : null)), ...fc.map((p) => p.aqi)];
    const upperBand = [...recentSlice.map((_, i) => (i === recentSlice.length - 1 ? pAqi(recentSlice[i]) : null)), ...fc.map((p) => p.confidence_high)];
    const lowerBand = [...recentSlice.map((_, i) => (i === recentSlice.length - 1 ? pAqi(recentSlice[i]) : null)), ...fc.map((p) => p.confidence_low)];

    function pAqi(pt) {
      return pt ? pt.aqi : null;
    }

    renderOrReplaceChart("vmInsightsForecastChart", {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Recent Measured Hourly AQI",
            data: histSeries,
            borderColor: "#10343b",
            backgroundColor: "rgba(16, 52, 59, 0.1)",
            tension: 0.3,
            pointRadius: 3,
          },
          {
            label: "Upper Uncertainty Bound",
            data: upperBand,
            borderColor: "rgba(14, 165, 233, 0.3)",
            borderDash: [2, 4],
            pointRadius: 0,
            fill: false,
          },
          {
            label: "24h Predicted AQI",
            data: fcSeries,
            borderColor: "#0ea5e9",
            borderDash: [6, 5],
            backgroundColor: "rgba(14, 165, 233, 0.16)",
            fill: "-1",
            tension: 0.3,
            pointRadius: 3,
          },
          {
            label: "Lower Uncertainty Bound",
            data: lowerBand,
            borderColor: "rgba(14, 165, 233, 0.3)",
            borderDash: [2, 4],
            backgroundColor: "rgba(14, 165, 233, 0.10)",
            fill: "-1",
            pointRadius: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { beginAtZero: true, title: { display: true, text: "AQI" } } },
      },
    });
  }

  /* =========================================================
     3. SMART CLEAN-AIR NAVIGATION (routes.html)
     ========================================================= */
  let routeMap = null;
  let routeLayerGroup = null;

  async function initRoutesPage() {
    const mapEl = document.getElementById("vmRouteMap");
    if (mapEl && typeof window.L !== "undefined") {
      routeMap = window.L.map("vmRouteMap", {
        minZoom: 4,
        maxBounds: [
          [5.5, 67.0],
          [38.5, 98.5],
        ],
        maxBoundsViscosity: 0.8,
      }).setView([19.076, 72.8777], 12);
      window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
        maxZoom: 18,
      }).addTo(routeMap);
      routeLayerGroup = window.L.layerGroup().addTo(routeMap);
    }

    let selectedMode = "walking";
    const modeButtons = document.querySelectorAll(".vm-mode-btn");
    modeButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        modeButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        selectedMode = btn.getAttribute("data-mode") || "walking";
      });
    });

    const escapeToggle = document.getElementById("vmEscapeModeToggle");
    const originInput = document.getElementById("vmRouteOrigin");
    const destInput = document.getElementById("vmRouteDest");
    const swapBtn = document.getElementById("vmSwapRouteBtn");

    if (swapBtn && originInput && destInput) {
      swapBtn.addEventListener("click", async () => {
        const tmp = originInput.value;
        originInput.value = destInput.value;
        destInput.value = tmp;
        const oVal = originInput.value.trim();
        const dVal = destInput.value.trim();
        if (oVal && dVal) {
          await searchRoutes(oVal, dVal, selectedMode, escapeToggle ? escapeToggle.checked : false);
        }
      });
    }

    const form = document.getElementById("vmRouteSearchForm");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const origin = (originInput ? originInput.value : "").trim();
        const destination = (destInput ? destInput.value : "").trim();
        if (!origin || !destination) {
          window.VayuMain.showBanner("vmRoutesBanner", "Please enter both a starting location and destination.", "error");
          return;
        }
        await searchRoutes(origin, destination, selectedMode, escapeToggle ? escapeToggle.checked : false);
      });
    }

    if (escapeToggle) {
      escapeToggle.addEventListener("change", async () => {
        const origin = (originInput ? originInput.value : "").trim();
        const destination = (destInput ? destInput.value : "").trim();
        if (origin && destination) {
          await searchRoutes(origin, destination, selectedMode, escapeToggle.checked);
        }
      });
    }

    const urlEscape = new URLSearchParams(window.location.search).get("escape") === "1";
    if (escapeToggle && urlEscape) {
      escapeToggle.checked = true;
    }

    await searchRoutes("Bandra, Mumbai", "Colaba, Mumbai", selectedMode, escapeToggle ? escapeToggle.checked : false);
  }

  async function searchRoutes(origin, destination, mode, escapeMode) {
    const submitBtn = document.getElementById("vmRouteSubmitBtn");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = escapeMode ? "Finding Safe Escape..." : "Finding Routes...";
    }
    window.VayuMain.showBanner("vmRoutesBanner", "", "info");
    try {
      const data = await window.VayuApi.getRoutes({ origin, destination, mode, escape_mode: escapeMode });
      renderRoutesResult(data);
    } catch (err) {
      window.VayuMain.showBanner("vmRoutesBanner", err.message || "Unable to compute routes.", "error");
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Find Cleaner Route";
      }
    }
  }

  function updateSelectedRouteMetrics(routeObj, data) {
    const avgAqi = routeObj ? routeObj.avg_aqi : null;
    const cat = naqiCategoryFromValue(avgAqi);
    const pointerEl = document.getElementById("vmRouteSpectrumPointer");
    if (pointerEl) {
      const pct = avgAqi != null ? Math.min(96, Math.max(4, Math.round((avgAqi / 400) * 100))) : 25;
      pointerEl.style.left = `${pct}%`;
    }

    const catEl = document.getElementById("vmRouteSelectedCategory");
    if (catEl) {
      catEl.className = `vm-status-tag ${levelBadgeClass(cat)}`;
      catEl.textContent = cat;
    }

    setText("vmRouteSelectedAvgAqi", avgAqi != null ? `Avg AQI ${avgAqi}` : "Avg AQI N/A");
    setText(
      "vmMapStatusBadge",
      routeObj ? `${routeObj.label}: ${avgAqi != null ? `AQI ${avgAqi}` : `${routeObj.duration_min} min`}` : "Live AQI Checkpoints"
    );

    const tipsEl = document.getElementById("vmRouteTipsList");
    if (tipsEl && routeObj) {
      const tips = [];
      if (avgAqi != null && avgAqi > 150) {
        tips.push("Wear an N95 mask along this corridor due to elevated AQI.");
      } else {
        tips.push(`Air quality along ${routeObj.label} is ${cat.toLowerCase()} for ${data.mode || "travel"}.`);
      }
      if ((routeObj.incident_hits || 0) > 0) {
        tips.push(`Route passes near ${routeObj.incident_hits} reported pollution incident(s) — stay alert.`);
      } else {
        tips.push("No active citizen hotspot incidents detected directly on this path.");
      }
      if (data.best_travel_time) {
        tips.push(`Best upcoming clean window: ${window.VayuMain.formatHourLabel(data.best_travel_time.time)} (AQI ${data.best_travel_time.aqi}).`);
      }
      tipsEl.innerHTML = tips
        .map((t) => `<li><span class="vm-check-ico">&check;</span><span>${window.VayuMain.escapeHtml(t)}</span></li>`)
        .join("");
    }
  }

  function renderRoutesResult(data) {
    setText("vmRouteSummaryNote", data.recommendation_note || "");

    const escBox = document.getElementById("vmEscapeAdvisoryBox");
    const esc = data.emergency_escape || {};
    if (escBox) {
      if (data.escape_mode || (esc.nearby_hotspot_count || 0) > 0) {
        escBox.classList.remove("vm-hidden");
        escBox.innerHTML = `
          <strong>${data.escape_mode ? "Emergency Escape Active" : "Hotspot Alert"}:</strong>
          ${window.VayuMain.escapeHtml(esc.advice || "")}
        `;
      } else {
        escBox.classList.add("vm-hidden");
      }
    }

    const bestWinEl = document.getElementById("vmRouteBestTime");
    if (bestWinEl) {
      if (data.best_travel_time) {
        bestWinEl.textContent = `${window.VayuMain.formatHourLabel(data.best_travel_time.time)} · AQI ${data.best_travel_time.aqi} (${data.best_travel_time.category})`;
      } else {
        bestWinEl.textContent = "Forecast travel window unavailable.";
      }
    }

    const destAir = data.destination_air || null;
    setText("vmDestAqiValue", destAir && destAir.aqi != null ? String(destAir.aqi) : "--");
    const destBadge = document.getElementById("vmDestAqiBadge");
    if (destBadge) {
      const dCat = destAir && destAir.category ? destAir.category : "Unavailable";
      destBadge.className = `vm-status-tag ${levelBadgeClass(dCat)}`;
      destBadge.textContent = dCat;
    }
    setText(
      "vmDestTempVal",
      destAir && destAir.temperature != null ? `${Number(destAir.temperature).toFixed(1)}${destAir.temp_unit || "°C"}` : "--"
    );
    setText("vmDestWeatherCond", destAir && destAir.condition ? destAir.condition : "--");

    const winGrid = document.getElementById("vmCleanWindowsGrid");
    if (winGrid) {
      const windows = data.clean_air_windows || [];
      if (!windows.length) {
        winGrid.innerHTML = `<article class="vm-card">24-hour forecast windows unavailable right now.</article>`;
      } else {
        winGrid.innerHTML = windows
          .map((w) => {
            const stCls = w.status === "Avoid" ? "vm-status-worse" : w.status === "Caution" ? "vm-status-moderate" : "vm-status-good";
            return `
              <article class="vm-card">
                <div class="vm-aqi-header-row" style="margin-bottom:6px;">
                  <span class="vm-stat-label">${window.VayuMain.escapeHtml(w.label)}</span>
                  <span class="vm-status-tag ${stCls}">${window.VayuMain.escapeHtml(w.status)}</span>
                </div>
                <div class="vm-stat-value tabular-nums" style="font-size:1.3rem;">${window.VayuMain.formatHourLabel(w.time)} · AQI ${w.aqi}</div>
                <p class="vm-section-subtitle" style="margin-top:6px;">${window.VayuMain.escapeHtml(w.guidance)}</p>
              </article>
            `;
          })
          .join("");
      }
    }

    const cardsEl = document.getElementById("vmRouteCards");
    const routes = data.routes || [];
    const defaultSelectedIdx = Math.max(0, routes.findIndex((r) => r.route_type === "safe_air" || r.is_recommended));
    if (cardsEl) {
      cardsEl.innerHTML = routes
        .map((r, idx) => {
          const isSafe = r.route_type === "safe_air";
          const isSel = idx === defaultSelectedIdx;
          const badgeHtml = isSafe
            ? `<span class="vm-status-tag vm-status-good">${data.escape_mode ? "Escape Safe Air" : "Safe Air"}</span>`
            : `<span class="vm-status-tag vm-status-moderate">Standard</span>`;
          const routeIcon = isSafe
            ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"></path><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"></path></svg>`
            : `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"></path><circle cx="7" cy="17" r="2"></circle><path d="M9 17h6"></path><circle cx="17" cy="17" r="2"></circle></svg>`;
          return `
            <div class="vm-route-option ${isSafe ? "safe-air" : ""} ${r.is_recommended ? "recommended" : ""} ${isSel ? "selected" : ""}" data-route-idx="${idx}">
              <div class="vm-aqi-header-row" style="margin-bottom:6px;">
                <span class="vm-title-with-ico" style="gap:8px;">
                  ${routeIcon}
                  <strong>${window.VayuMain.escapeHtml(r.label)}</strong>
                </span>
                ${badgeHtml}
              </div>
              <div class="vm-meta-line" style="margin-bottom:6px;">
                <strong class="tabular-nums" style="color:var(--vm-ink-primary);">${r.duration_min} min</strong>
                <span>·</span>
                <span class="tabular-nums">${r.distance_km} km (${window.VayuMain.escapeHtml(data.mode)})</span>
                <span>·</span>
                <span class="tabular-nums">AQI: ${r.avg_aqi != null ? r.avg_aqi : "N/A"}</span>
                <span>·</span>
                <span class="tabular-nums">Hotspots: ${r.incident_hits ?? 0}</span>
              </div>
              <p class="vm-section-subtitle">${window.VayuMain.escapeHtml(r.recommendation_reason || "")}</p>
            </div>
          `;
        })
        .join("");

      cardsEl.querySelectorAll(".vm-route-option").forEach((card) => {
        card.addEventListener("click", () => {
          cardsEl.querySelectorAll(".vm-route-option").forEach((c) => c.classList.remove("selected"));
          card.classList.add("selected");
          const idx = Number(card.getAttribute("data-route-idx"));
          drawRoutesOnMap(data, idx);
          updateSelectedRouteMetrics(routes[idx], data);
        });
      });
    }

    updateSelectedRouteMetrics(routes[defaultSelectedIdx], data);

    const hotspots = data.hotspot_zones || [];
    setText("vmRouteHotspotCount", `${hotspots.length} Active`);
    const hotspotsEl = document.getElementById("vmRoutesHotspotsList");
    if (hotspotsEl) {
      hotspotsEl.innerHTML = hotspots.length
        ? hotspots
            .slice(0, 8)
            .map(
              (h) => `
              <li>
                <div class="vm-aqi-header-row" style="margin-bottom:4px;">
                  <strong>${window.VayuMain.escapeHtml(h.title || h.hotspot_type || "Hotspot")}</strong>
                  <span class="vm-status-tag ${h.is_verified ? "vm-status-bad" : "vm-status-moderate"}">${window.VayuMain.escapeHtml(h.hotspot_type || "Hotspot")}</span>
                </div>
                <div class="vm-meta-line">
                  ${h.aqi != null ? `<span>AQI ${h.aqi} (${window.VayuMain.escapeHtml(h.category || "")})</span>` : ""}
                  ${h.location_name ? `<span>${window.VayuMain.escapeHtml(h.location_name)}</span>` : ""}
                </div>
              </li>
            `
            )
            .join("")
        : `<li>No high-AQI hotspots along this corridor.</li>`;
    }

    const incListEl = document.getElementById("vmRoutesIncidentsList");
    const incUpdates = data.incident_updates || [];
    if (incListEl) {
      incListEl.innerHTML = incUpdates.length
        ? incUpdates
            .map(
              (inc) => `
              <li>
                <div class="vm-aqi-header-row" style="margin-bottom:4px;">
                  <strong>${window.VayuMain.escapeHtml(inc.title)}</strong>
                  <span class="vm-badge-data ${inc.is_verified ? "vm-badge-verified" : "vm-badge-unverified"}">${window.VayuMain.escapeHtml(inc.status)}</span>
                </div>
                <div class="vm-meta-line">
                  <span class="font-mono">${window.VayuMain.escapeHtml(inc.report_code)}</span>
                  <span>·</span>
                  <span>${window.VayuMain.escapeHtml(inc.category)}</span>
                  <span>·</span>
                  <span>${window.VayuMain.escapeHtml(inc.location_name)}</span>
                </div>
              </li>
            `
            )
            .join("")
        : `<li>No active community incident updates reported yet.</li>`;
    }

    drawRoutesOnMap(data, defaultSelectedIdx);
  }

  function drawRoutesOnMap(data, selectedIdx) {
    if (!routeMap || !routeLayerGroup || typeof window.L === "undefined") return;
    routeLayerGroup.clearLayers();
    const bounds = [];

    (data.routes || []).forEach((r, idx) => {
      const coords = (r.geometry && r.geometry.coordinates ? r.geometry.coordinates : []).map((c) => [c[1], c[0]]);
      if (!coords.length) return;
      const isSelected = idx === selectedIdx;
      const isSafe = r.route_type === "safe_air";
      const color = isSafe ? "#16A34A" : "#475569";
      const line = window.L.polyline(coords, {
        color,
        weight: isSelected ? 6 : 4,
        opacity: isSelected ? 0.94 : 0.62,
        dashArray: isSafe ? null : "6, 8",
      }).addTo(routeLayerGroup);
      line.bindPopup(`<strong>${window.VayuMain.escapeHtml(r.label)}</strong><br>${r.duration_min} min · ${r.distance_km} km<br>Avg AQI: ${r.avg_aqi ?? "N/A"}`);
      coords.forEach((pt) => bounds.push(pt));

      if (isSelected) {
        (r.waypoints || []).forEach((w, wIdx) => {
          const markerColor = aqiColorHex(w.aqi);
          const circle = window.L.circleMarker([w.lat, w.lon], {
            radius: w.aqi > 100 ? 9 : 7,
            color: "#ffffff",
            weight: 2,
            fillColor: markerColor,
            fillOpacity: 0.95,
          }).addTo(routeLayerGroup);
          circle.bindPopup(
            `<strong>Checkpoint ${wIdx + 1}</strong><br>AQI: ${w.aqi} (${w.category})<br>PM2.5: ${w.pm2_5 ?? "N/A"} µg/m³`
          );
        });
      }
    });

    (data.hotspot_zones || []).forEach((hz) => {
      if (hz.lat == null || hz.lon == null) return;
      const isVerified = Boolean(hz.is_verified);
      window.L.circle([hz.lat, hz.lon], {
        radius: 1200,
        color: isVerified ? "#DC2626" : "#D97706",
        fillColor: isVerified ? "#EF4444" : "#F59E0B",
        fillOpacity: 0.22,
        weight: 2,
      })
        .addTo(routeLayerGroup)
        .bindPopup(`<strong>${window.VayuMain.escapeHtml(hz.hotspot_type)}</strong><br>${window.VayuMain.escapeHtml(hz.title || "")}`);
      bounds.push([hz.lat, hz.lon]);
    });

    if (data.origin) {
      window.L.marker([data.origin.latitude, data.origin.longitude])
        .addTo(routeLayerGroup)
        .bindPopup(`<strong>Start:</strong> ${window.VayuMain.escapeHtml(data.origin.name)}`);
    }
    if (data.destination) {
      window.L.marker([data.destination.latitude, data.destination.longitude])
        .addTo(routeLayerGroup)
        .bindPopup(`<strong>Destination:</strong> ${window.VayuMain.escapeHtml(data.destination.name)}`);
    }

    if (bounds.length) {
      routeMap.fitBounds(bounds, { padding: [36, 36] });
    }
  }

  /* =========================================================
     4. AIR GUARDIAN NETWORK / COMMUNITY (community.html)
     ========================================================= */
  let communityMap = null;
  let communityLayerGroup = null;
  let cachedCommunityReports = [];
  let activeCommunityMapCategory = "";

  const CITY_COORDS_FALLBACK = {
    mumbai: [19.076, 72.8777],
    delhi: [28.6139, 77.209],
    bengaluru: [12.9716, 77.5946],
    bangalore: [12.9716, 77.5946],
    pune: [18.5204, 73.8567],
    chennai: [13.0827, 80.2707],
    kolkata: [22.5726, 88.3639],
    hyderabad: [17.385, 78.4867],
    ahmedabad: [23.0225, 72.5714],
    jaipur: [26.9124, 75.7873],
    lucknow: [26.8467, 80.9462],
    indore: [22.7196, 75.8577],
    surat: [21.1702, 72.8311],
    nagpur: [21.1458, 79.0882],
    patna: [25.5941, 85.1376],
    bhopal: [23.2599, 77.4126],
  };

  function resolveReportCoords(report) {
    if (report.latitude != null && report.longitude != null) {
      return [Number(report.latitude), Number(report.longitude)];
    }
    const locStr = String(report.location_name || "").toLowerCase();
    for (const [key, coords] of Object.entries(CITY_COORDS_FALLBACK)) {
      if (locStr.includes(key)) {
        // deterministic tiny jitter so multiple city reports don't overlap identically
        const jitter = ((Number(report.id || 1) % 7) - 3) * 0.008;
        return [coords[0] + jitter, coords[1] - jitter];
      }
    }
    return null;
  }

  function communityCategoryColor(cat) {
    const c = String(cat || "").toLowerCase();
    if (c.includes("smoke") || c.includes("garbage")) return "#EA580C";
    if (c.includes("dust") || c.includes("construction")) return "#D97706";
    if (c.includes("industrial") || c.includes("vehicle")) return "#7C3AED";
    return "#16A34A";
  }

  function drawCommunityMap(reports) {
    if (!communityMap || !communityLayerGroup || typeof window.L === "undefined") return;
    communityLayerGroup.clearLayers();

    const filtered = activeCommunityMapCategory
      ? reports.filter((r) => String(r.category || "").toLowerCase() === activeCommunityMapCategory.toLowerCase())
      : reports;

    const bounds = [];
    filtered.forEach((r) => {
      const pt = resolveReportCoords(r);
      if (!pt) return;
      bounds.push(pt);
      const color = communityCategoryColor(r.category);
      const marker = window.L.circleMarker(pt, {
        radius: 9,
        color: "#ffffff",
        weight: 2.5,
        fillColor: color,
        fillOpacity: 0.94,
      }).addTo(communityLayerGroup);

      marker.bindPopup(`
        <strong>${window.VayuMain.escapeHtml(r.title)}</strong><br>
        <span>${window.VayuMain.escapeHtml(r.category)} &middot; ${window.VayuMain.escapeHtml(r.status)}</span><br>
        <small>${window.VayuMain.escapeHtml(r.location_name)}</small>
      `);
    });

    if (bounds.length > 1) {
      communityMap.fitBounds(bounds, { padding: [36, 36], maxZoom: 13 });
    } else if (bounds.length === 1) {
      communityMap.setView(bounds[0], 12);
    } else {
      communityMap.setView([20.5937, 78.9629], 5);
    }
  }

  async function initCommunityPage() {
    const mapEl = document.getElementById("vmCommunityMap");
    if (mapEl && typeof window.L !== "undefined") {
      communityMap = window.L.map("vmCommunityMap", {
        minZoom: 4,
        maxBounds: [
          [5.5, 67.0],
          [38.5, 98.5],
        ],
        maxBoundsViscosity: 0.8,
      }).setView([20.5937, 78.9629], 5);
      window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
        maxZoom: 18,
      }).addTo(communityMap);
      communityLayerGroup = window.L.layerGroup().addTo(communityMap);
    }

    const form = document.getElementById("vmCommunityForm");
    const photoInput = document.getElementById("vmReportPhoto");
    const previewImg = document.getElementById("vmPhotoPreview");
    const useLocBtn = document.getElementById("vmReportUseLocBtn");
    const locInput = document.getElementById("vmReportLocation");
    const latInput = document.getElementById("vmReportLat");
    const lonInput = document.getElementById("vmReportLon");

    const searchInput = document.getElementById("vmCommSearchInput");
    const statusFilter = document.getElementById("vmCommStatusFilter");
    const catFilter = document.getElementById("vmCommCategoryFilter");

    document.querySelectorAll("#vmCommMapPills .vm-map-pill").forEach((pill) => {
      pill.addEventListener("click", () => {
        document.querySelectorAll("#vmCommMapPills .vm-map-pill").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        activeCommunityMapCategory = pill.getAttribute("data-cat") || "";
        drawCommunityMap(cachedCommunityReports);
      });
    });

    function getFilterParams() {
      return {
        search: searchInput ? searchInput.value.trim() : "",
        status: statusFilter ? statusFilter.value : "",
        category: catFilter ? catFilter.value : "",
      };
    }

    if (searchInput) searchInput.addEventListener("input", () => loadCommunityReports(getFilterParams()));
    if (statusFilter) statusFilter.addEventListener("change", () => loadCommunityReports(getFilterParams()));
    if (catFilter) catFilter.addEventListener("change", () => loadCommunityReports(getFilterParams()));

    if (photoInput && previewImg) {
      photoInput.addEventListener("change", () => {
        const file = photoInput.files && photoInput.files[0];
        if (!file) {
          previewImg.classList.add("vm-hidden");
          previewImg.removeAttribute("src");
          return;
        }
        const allowed = ["image/png", "image/jpeg", "image/webp"];
        if (!allowed.includes(file.type)) {
          window.VayuMain.showBanner("vmCommunityBanner", "Only PNG, JPG, JPEG, or WEBP photos are allowed.", "error");
          photoInput.value = "";
          previewImg.classList.add("vm-hidden");
          return;
        }
        if (file.size > 5 * 1024 * 1024) {
          window.VayuMain.showBanner("vmCommunityBanner", "Photo file size must be 5 MB or smaller.", "error");
          photoInput.value = "";
          previewImg.classList.add("vm-hidden");
          return;
        }
        const reader = new FileReader();
        reader.onload = (ev) => {
          previewImg.src = ev.target.result;
          previewImg.classList.remove("vm-hidden");
        };
        reader.readAsDataURL(file);
      });
    }

    if (useLocBtn && locInput) {
      useLocBtn.addEventListener("click", async () => {
        useLocBtn.disabled = true;
        try {
          const coords = await window.VayuMain.requestBrowserLocation();
          if (latInput) latInput.value = String(coords.lat);
          if (lonInput) lonInput.value = String(coords.lon);
          const aq = await window.VayuApi.getAirQuality({ lat: coords.lat, lon: coords.lon });
          locInput.value = aq.location ? aq.location.name : `${coords.lat.toFixed(4)}, ${coords.lon.toFixed(4)}`;
        } catch (err) {
          window.VayuMain.showBanner("vmCommunityBanner", err.message, "error");
        } finally {
          useLocBtn.disabled = false;
        }
      });
    }

    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        window.VayuMain.showBanner("vmCommunityBanner", "", "info");
        const title = document.getElementById("vmReportTitle").value.trim();
        const category = document.getElementById("vmReportCategory").value;
        const locationName = locInput.value.trim();
        const description = document.getElementById("vmReportDesc").value.trim();

        if (title.length < 4 || description.length < 10 || locationName.length < 2) {
          window.VayuMain.showBanner(
            "vmCommunityBanner",
            "Please fill in a descriptive title (min 4 chars), location, and details (min 10 chars).",
            "error"
          );
          return;
        }

        const fd = new FormData();
        fd.append("title", title);
        fd.append("category", category);
        fd.append("location_name", locationName);
        fd.append("description", description);
        if (latInput && latInput.value) fd.append("latitude", latInput.value);
        if (lonInput && lonInput.value) fd.append("longitude", lonInput.value);
        if (photoInput && photoInput.files && photoInput.files[0]) {
          fd.append("photo", photoInput.files[0]);
        }

        const submitBtn = document.getElementById("vmReportSubmitBtn");
        if (submitBtn) submitBtn.disabled = true;
        try {
          const res = await window.VayuApi.submitCommunityReport(fd);
          window.VayuMain.showBanner("vmCommunityBanner", `Report ${res.report.report_code} submitted.`, "success");
          form.reset();
          if (previewImg) previewImg.classList.add("vm-hidden");
          await loadCommunityReports(getFilterParams());
        } catch (err) {
          window.VayuMain.showBanner("vmCommunityBanner", err.message || "Failed to submit report.", "error");
        } finally {
          if (submitBtn) submitBtn.disabled = false;
        }
      });
    }

    await loadCommunityReports(getFilterParams());
  }

  function communityCategoryClass(cat) {
    const c = String(cat || "").toLowerCase();
    if (c.includes("smoke")) return "cat-smoke";
    if (c.includes("dust") || c.includes("construction")) return "cat-dust";
    if (c.includes("industrial")) return "cat-industrial";
    if (c.includes("garbage") || c.includes("waste")) return "cat-garbage";
    if (c.includes("vehicle") || c.includes("traffic")) return "cat-vehicle";
    return "cat-other";
  }

  async function loadCommunityReports(filters) {
    const feedEl = document.getElementById("vmCommunityFeed");
    const previewEl = document.getElementById("vmCommunityRecentPreview");
    if (!feedEl) return;
    try {
      const data = await window.VayuApi.getCommunityReports(filters || {});
      const reports = data.reports || [];
      cachedCommunityReports = reports;
      const contrib = data.contribution_summary || {};

      setText("commTotalCount", String(contrib.total_reports ?? reports.length));
      setText("commGuardianTier", contrib.guardian_tier || "Bronze Air Guardian");
      setText("commGuardianPoints", `${contrib.guardian_points ?? 0} pts`);
      setText("commVerifiedCount", `${(contrib.verified_count || 0) + (contrib.resolved_count || 0)}`);
      setText("commPendingCount", `${contrib.pending_count ?? 0}`);
      setText("vmReportsCount", `${reports.length} report${reports.length === 1 ? "" : "s"}`);

      drawCommunityMap(reports);

      if (previewEl) {
        previewEl.innerHTML = reports.length
          ? reports
              .slice(0, 3)
              .map((r) => {
                const stCls =
                  r.status === "Resolved" || r.status === "Verified"
                    ? "vm-status-good"
                    : r.status === "Under Review"
                    ? "vm-status-moderate"
                    : "vm-status-bad";
                return `
                  <div class="vm-twin-item-row" style="padding:10px 12px;">
                    <div style="min-width:0;">
                      <strong style="display:block; font-size:0.9rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${window.VayuMain.escapeHtml(r.title)}</strong>
                      <div class="vm-meta-line">${window.VayuMain.escapeHtml(r.location_name)} &middot; ${window.VayuMain.formatDateTime(r.created_at)}</div>
                    </div>
                    <span class="vm-status-tag ${stCls}">${window.VayuMain.escapeHtml(r.status)}</span>
                  </div>
                `;
              })
              .join("")
          : `<span class="vm-meta-line">No citizen reports logged yet.</span>`;
      }

      if (reports.length === 0) {
        feedEl.innerHTML = `
          <div class="vm-card">
            <strong>No reports found yet.</strong>
            <p class="vm-section-subtitle">Use the form to report a local pollution incident or clear active filters.</p>
          </div>
        `;
        return;
      }

      feedEl.innerHTML = reports
        .map((r) => {
          const statusCls =
            r.status === "Resolved" || r.status === "Verified"
              ? "vm-status-good"
              : r.status === "Under Review"
              ? "vm-status-moderate"
              : r.status === "Rejected"
              ? "vm-status-worse"
              : "vm-status-bad";
          const vBadgeCls = r.is_verified ? "vm-badge-verified" : "vm-badge-unverified";
          const catCls = communityCategoryClass(r.category);
          return `
          <article class="vm-report-item ${catCls}">
            <div>
              <div class="vm-aqi-header-row" style="margin-bottom:8px;">
                <strong style="font-size:1.02rem;">${window.VayuMain.escapeHtml(r.title)}</strong>
                <div style="display:flex; gap:6px; flex-wrap:wrap;">
                  <span class="vm-cat-chip">${window.VayuMain.escapeHtml(r.category)}</span>
                  <span class="vm-status-tag ${statusCls}">${window.VayuMain.escapeHtml(r.status)}</span>
                </div>
              </div>
              <div class="vm-meta-line" style="margin-bottom:8px;">
                <span class="font-mono">${window.VayuMain.escapeHtml(r.report_code)}</span>
                <span>·</span>
                <span>${window.VayuMain.escapeHtml(r.location_name)}</span>
                <span>·</span>
                <span>${window.VayuMain.formatDateTime(r.created_at)}</span>
                <span>·</span>
                <span class="vm-badge-data ${vBadgeCls}">${window.VayuMain.escapeHtml(r.verification_label || r.status)}</span>
              </div>
              <p style="font-size:0.92rem; color:#235059; margin-bottom:10px;">${window.VayuMain.escapeHtml(r.description)}</p>
              <div class="vm-meta-line">
                <label for="status-${r.id}" style="font-weight:600;">Status:</label>
                <select id="status-${r.id}" class="vm-select vm-report-status-select" data-id="${r.id}" style="width:auto; padding:5px 10px; font-size:0.84rem;">
                  <option value="Submitted" ${r.status === "Submitted" ? "selected" : ""}>Submitted</option>
                  <option value="Under Review" ${r.status === "Under Review" ? "selected" : ""}>Under Review</option>
                  <option value="Verified" ${r.status === "Verified" ? "selected" : ""}>Verified</option>
                  <option value="Resolved" ${r.status === "Resolved" ? "selected" : ""}>Resolved</option>
                  <option value="Rejected" ${r.status === "Rejected" ? "selected" : ""}>Rejected</option>
                </select>
              </div>
            </div>
            ${
              r.photo_url
                ? `<img src="${window.VayuMain.escapeHtml(r.photo_url)}" alt="Photo for ${window.VayuMain.escapeHtml(r.title)}" class="vm-report-thumb" />`
                : ""
            }
          </article>
        `;
        })
        .join("");

      feedEl.querySelectorAll(".vm-report-status-select").forEach((sel) => {
        sel.addEventListener("change", async () => {
          const rid = Number(sel.getAttribute("data-id"));
          try {
            await window.VayuApi.updateReportStatus(rid, sel.value);
            await loadCommunityReports(filters);
          } catch (err) {
            window.VayuMain.showBanner("vmCommunityBanner", err.message, "error");
          }
        });
      });
    } catch (err) {
      feedEl.innerHTML = `<div class="vm-banner vm-banner-error">${window.VayuMain.escapeHtml(err.message)}</div>`;
    }
  }

  /* =========================================================
     5. POLLUTION EMERGENCY SYSTEM (alerts.html)
     ========================================================= */
  let alertMap = null;
  let alertLayerGroup = null;

  async function initAlertsPage() {
    const mapEl = document.getElementById("vmAlertMap");
    if (mapEl && typeof window.L !== "undefined") {
      alertMap = window.L.map("vmAlertMap", {
        minZoom: 4,
        maxBounds: [
          [5.5, 67.0],
          [38.5, 98.5],
        ],
        maxBoundsViscosity: 0.8,
      }).setView([19.076, 72.8777], 11);
      window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
        maxZoom: 18,
      }).addTo(alertMap);
      alertLayerGroup = window.L.layerGroup().addTo(alertMap);
    }

    const precautionsBtn = document.getElementById("vmAlertTakePrecautionsBtn");
    const precautionsPanel = document.getElementById("vmPrecautionsDetailPanel");
    const closePrecautionsBtn = document.getElementById("vmClosePrecautionsBtn");

    if (precautionsBtn && precautionsPanel) {
      precautionsBtn.addEventListener("click", () => {
        const isHidden = precautionsPanel.classList.contains("vm-hidden");
        precautionsPanel.classList.toggle("vm-hidden", !isHidden);
        precautionsBtn.setAttribute("aria-expanded", String(isHidden));
        if (isHidden) {
          precautionsPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      });
    }

    if (closePrecautionsBtn && precautionsPanel && precautionsBtn) {
      closePrecautionsBtn.addEventListener("click", () => {
        precautionsPanel.classList.add("vm-hidden");
        precautionsBtn.setAttribute("aria-expanded", "false");
      });
    }

    async function loadAlerts(isInitial) {
      const params = window.VayuMain.getStoredLocationParams();
      try {
        const data = await window.VayuApi.getAlerts(params);
        window.VayuMain.updateHeaderWeather(data);
        renderAlertsPage(data);
      } catch (err) {
        if (isInitial && (params.city || params.lat != null)) {
          window.VayuMain.clearStoredLocation();
          window.VayuMain.updateCityBackground("Mumbai");
          try {
            const fallback = await window.VayuApi.getAlerts({ city: "Mumbai" });
            window.VayuMain.updateHeaderWeather(fallback);
            renderAlertsPage(fallback);
            window.VayuMain.showBanner("vmAlertsBanner", "VayuMitra supports locations within India only. Showing Mumbai.", "info");
            return;
          } catch (_e) {}
        }
        window.VayuMain.showBanner("vmAlertsBanner", err.message || "Unable to load alerts.", "error");
      }
    }

    window.addEventListener("vayumitra:citychange", () => loadAlerts(false));
    await loadAlerts(true);
  }

  function renderAlertsPage(data) {
    const cls = data.classification || {};
    const loc = data.location || {};
    const liveAlerts = data.live_alerts || [];
    const aqi = data.current_aqi;

    setText("alertsLocation", loc.name || "—");
    setText("alertsCurrentAqi", `${aqi ?? "--"} (${cls.category || "Unavailable"})`);
    setText("alertsUpdatedAt", window.VayuMain.formatDateTime(data.recorded_at));

    const heroStrip = document.getElementById("vmAlertHeroStrip");
    const isElevated = liveAlerts.length > 0 || (aqi != null && aqi > 150);
    if (heroStrip) {
      heroStrip.classList.toggle("is-ok", !isElevated);
    }
    const precPanel = document.getElementById("vmPrecautionsDetailPanel");
    if (precPanel) {
      precPanel.classList.toggle("is-ok", !isElevated);
    }
    setText("vmAlertTakePrecautionsLabel", "Take Precautions");
    setText(
      "vmAlertHeroTitle",
      liveAlerts.length > 0
        ? liveAlerts[0].alert_title || "High Pollution Alert!"
        : `Air Quality Status: ${cls.category || "Good"} in ${loc.name || "Your Area"}`
    );
    setText(
      "vmAlertHeroDesc",
      liveAlerts.length > 0
        ? liveAlerts[0].description
        : `AQI in ${loc.name || "your area"} is ${aqi ?? "--"} (${cls.category || "Good"}).`
    );

    const riskScore = data.risk_score;
    const riskLevel = data.risk_level || "Low Risk";
    setText("vmAlertRiskScorePill", riskScore != null ? `Risk Score: ${riskScore}/100` : "Risk Score: --");
    const riskExplainEl = document.getElementById("vmAlertRiskExplain");
    if (riskExplainEl) {
      riskExplainEl.innerHTML = `<strong>Risk Score (${riskScore != null ? `${riskScore}/100` : "--"} &middot; ${window.VayuMain.escapeHtml(riskLevel)}):</strong> ${window.VayuMain.escapeHtml(
        data.risk_explanation || "Computed from live AQI, PM2.5 levels, and nearby citizen reports."
      )}`;
    }

    const measuresGrid = document.getElementById("vmPrecautionsMeasuresGrid");
    if (measuresGrid) {
      setText(
        "vmPrecautionsPanelIntro",
        `Safety precautions & protective measures for ${loc.name || "your area"} (AQI ${aqi ?? "--"} · ${cls.category || "Current"}):`
      );
      const isSevere = aqi != null && aqi > 200;
      const isMod = aqi != null && aqi > 100;
      const precs = Array.isArray(cls.precautions) ? cls.precautions : [];
      const tiles = [
        {
          title: "Respiratory Mask",
          text: isSevere
            ? "Wear a well-fitted N95/N99 mask whenever stepping outside."
            : isMod
            ? "Carry an N95 mask for busy traffic corridors and dusty roads."
            : precs[2] || "No mask needed for healthy adults; sensitive groups keep one handy.",
          icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#15803d" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>`,
        },
        {
          title: "Outdoor Activity",
          text: isSevere
            ? "Avoid outdoor exercise, jogging, and prolonged exposure for children & elderly."
            : isMod
            ? "Reduce intense outdoor exertion during peak traffic hours."
            : precs[0] || "Safe for walking, jogging, and routine outdoor activities.",
          icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line></svg>`,
        },
        {
          title: "Indoor Protection",
          text: isSevere
            ? "Keep windows shut, run HEPA air purifiers indoors, and avoid incense/smoke."
            : isMod
            ? "Ventilate indoors only during midday clean-air windows and keep dust settled."
            : precs[1] || "Cross-ventilate rooms to maintain fresh indoor airflow.",
          icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>`,
        },
        {
          title: "Commute & Health",
          text: isMod
            ? "Pick Safe Air routes, use car AC recirculation, and stay well hydrated."
            : precs[3] || "Choose green corridors or public transit and stay hydrated.",
          icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"></path><circle cx="7" cy="17" r="2"></circle><circle cx="17" cy="17" r="2"></circle></svg>`,
        },
      ];
      measuresGrid.innerHTML = tiles
        .map(
          (t) => `
          <div class="vm-measure-tile">
            <div class="vm-title-with-ico" style="gap:8px;">
              ${t.icon}
              <strong>${t.title}</strong>
            </div>
            <p>${window.VayuMain.escapeHtml(t.text)}</p>
          </div>
        `
        )
        .join("");
    }

    renderAqiGaugeSvg("vmAlertAqiGauge", aqi, "Current AQI", cls.category);
    const maskStrip = document.getElementById("vmAlertMaskStrip");
    if (maskStrip) {
      maskStrip.classList.toggle("is-ok", !isElevated);
    }
    setText("vmAlertMaskNote", cls.recommendation || cls.message || "Monitor local air quality.");

    setText("alertDetailTime", window.VayuMain.formatDateTime(data.recorded_at));
    setText("alertDetailLocation", [loc.name, loc.admin1].filter(Boolean).join(", ") || loc.name || "—");
    setText(
      "alertDetailReason",
      data.alert_reason || (liveAlerts.length > 0 ? liveAlerts[0].description : "Regional emissions and weather conditions")
    );

    const riskBadge = document.getElementById("vmAlertsRiskBadge");
    if (riskBadge) {
      const riskText = aqi > 200 ? "Nearby Areas High Risk" : aqi > 100 ? "Nearby Areas Moderate Risk" : "Nearby Areas Low Risk";
      riskBadge.className = `vm-status-tag ${aqi > 200 ? "vm-status-worse" : aqi > 100 ? "vm-status-moderate" : "vm-status-good"}`;
      riskBadge.textContent = riskText;
    }

    if (alertMap && alertLayerGroup && typeof window.L !== "undefined" && loc.latitude != null && loc.longitude != null) {
      alertLayerGroup.clearLayers();
      const center = [loc.latitude, loc.longitude];
      const zoneColor = aqiColorHex(aqi);

      window.L.circle(center, {
        radius: 6000,
        color: zoneColor,
        fillColor: zoneColor,
        fillOpacity: 0.16,
        weight: 1.5,
      }).addTo(alertLayerGroup);

      window.L.circle(center, {
        radius: 2600,
        color: zoneColor,
        fillColor: zoneColor,
        fillOpacity: 0.28,
        weight: 2,
      })
        .addTo(alertLayerGroup)
        .bindPopup(`<strong>${window.VayuMain.escapeHtml(loc.name)}</strong><br>AQI: ${aqi ?? "--"} (${window.VayuMain.escapeHtml(cls.category || "")})`);

      window.L.marker(center).addTo(alertLayerGroup).bindPopup(`<strong>${window.VayuMain.escapeHtml(loc.name)}</strong><br>AQI ${aqi ?? "--"}`);

      (data.hotspot_updates || []).forEach((h) => {
        const pt = resolveReportCoords(h);
        if (!pt) return;
        window.L.circleMarker(pt, {
          radius: 7,
          color: "#ffffff",
          weight: 2,
          fillColor: h.is_verified ? "#DC2626" : "#D97706",
          fillOpacity: 0.9,
        })
          .addTo(alertLayerGroup)
          .bindPopup(`<strong>${window.VayuMain.escapeHtml(h.title)}</strong><br>${window.VayuMain.escapeHtml(h.location_name)}`);
      });

      alertMap.setView(center, 11);
    }

    const precEl = document.getElementById("vmAlertPrecautions");
    if (precEl) {
      const precs = cls.precautions || [];
      precEl.innerHTML = precs.length
        ? precs
            .map(
              (p) => `
              <li>
                <span class="vm-check-ico">&check;</span>
                <span>${window.VayuMain.escapeHtml(p)}</span>
              </li>
            `
            )
            .join("")
        : `<li><span class="vm-check-ico">&check;</span><span>Follow routine air-quality precautions.</span></li>`;
    }

    const liveEl = document.getElementById("vmLiveAlertsList");
    if (liveEl) {
      if (!liveAlerts.length) {
        liveEl.innerHTML = `<li><strong>All clear in ${window.VayuMain.escapeHtml(loc.name || "this area")}</strong><p class="vm-section-subtitle">No active warnings exceed current rules or your configured threshold.</p></li>`;
      } else {
        liveEl.innerHTML = liveAlerts
          .map(
            (a) => `
            <li>
              <div class="vm-aqi-header-row" style="margin-bottom:4px;">
                <strong>${window.VayuMain.escapeHtml(a.alert_title)}</strong>
                <span class="vm-status-tag ${levelBadgeClass(a.alert_level)}">${window.VayuMain.escapeHtml(a.alert_level)}</span>
              </div>
              <p class="vm-section-subtitle">${window.VayuMain.escapeHtml(a.description)}</p>
            </li>
          `
          )
          .join("");
      }
    }

    const hotspotEl = document.getElementById("vmAlertsHotspotsList");
    const hotspots = data.hotspot_updates || [];
    if (hotspotEl) {
      if (!hotspots.length) {
        hotspotEl.innerHTML = `<li>No active community hotspot reports logged yet.</li>`;
      } else {
        hotspotEl.innerHTML = hotspots
          .map(
            (h) => `
            <li>
              <div class="vm-aqi-header-row" style="margin-bottom:4px;">
                <strong>${window.VayuMain.escapeHtml(h.title)}</strong>
                <span class="vm-badge-data ${h.is_verified ? "vm-badge-verified" : "vm-badge-unverified"}">${window.VayuMain.escapeHtml(h.verification_label)}</span>
              </div>
              <div class="vm-meta-line">
                <span class="font-mono">${window.VayuMain.escapeHtml(h.report_code)}</span>
                <span>·</span>
                <span>${window.VayuMain.escapeHtml(h.category)}</span>
                <span>·</span>
                <span>${window.VayuMain.escapeHtml(h.location_name)}</span>
                <span>·</span>
                <span>${window.VayuMain.formatDateTime(h.created_at)}</span>
              </div>
            </li>
          `
          )
          .join("");
      }
    }

    const np = data.notification_preferences || {};
    setCheck("alertPrefEnabled", np.enabled);
    setCheck("alertPrefWarnings", np.aqi_warnings);
    setCheck("alertPrefLocation", np.location_alerts);
    setCheck("alertPrefBrowser", np.browser_notifications);
    setInputVal("alertPrefThreshold", np.aqi_threshold);
    setInputVal("alertPrefPm25", np.pm25_threshold);

    if (
      np.enabled &&
      np.browser_notifications &&
      liveAlerts.length > 0 &&
      "Notification" in window &&
      Notification.permission === "granted"
    ) {
      const topAlert = liveAlerts[0];
      const notifiedKey = `vm_notified_${topAlert.city}_${topAlert.metric}_${topAlert.created_at}`;
      if (!sessionStorage.getItem(notifiedKey)) {
        new Notification(`VayuMitra Alert: ${topAlert.alert_title}`, {
          body: topAlert.description,
        });
        sessionStorage.setItem(notifiedKey, "1");
      }
    }

    const histBody = document.getElementById("vmAlertHistoryBody");
    const history = data.alert_history || [];
    if (histBody) {
      if (!history.length) {
        histBody.innerHTML = `<tr><td colspan="5">No historical threshold alerts recorded yet.</td></tr>`;
      } else {
        histBody.innerHTML = history
          .map(
            (h) => `
            <tr>
              <td><strong>${window.VayuMain.escapeHtml(h.alert_title)}</strong></td>
              <td class="tabular-nums">${window.VayuMain.formatDateTime(h.created_at)}</td>
              <td>${window.VayuMain.escapeHtml(h.city)}</td>
              <td><span class="vm-status-tag ${levelBadgeClass(h.alert_level)}">${window.VayuMain.escapeHtml(h.alert_level)}</span></td>
              <td>${window.VayuMain.escapeHtml(h.description)}</td>
            </tr>
          `
          )
          .join("");
      }
    }
  }

  /* =========================================================
     6. ENVIRONMENTAL INTELLIGENCE REPORTS (reports.html)
     ========================================================= */
  async function initReportsPage() {

    let activePeriod = "daily";
    let dateFilter = { start_date: "", end_date: "", compare_city: "" };
    const segBtns = document.querySelectorAll(".vm-seg-btn");
    const exportBtn = document.getElementById("vmExportCsvBtn");
    const printBtn = document.getElementById("vmPrintReportBtn");
    const dateForm = document.getElementById("vmReportDateForm");
    const clearDatesBtn = document.getElementById("repClearDatesBtn");
    const compareInput = document.getElementById("repCompareCityInput");

    async function loadReports(period, extraParams, isInitial) {
      activePeriod = period;
      window.VayuMain.showBanner("vmReportsBanner", "", "info");
      const baseParams = window.VayuMain.getStoredLocationParams();
      try {
        const params = Object.assign({}, baseParams, dateFilter, extraParams || {}, { period });
        const data = await window.VayuApi.getReports(params);
        window.VayuMain.updateHeaderWeather(data);
        renderReportsData(data);
      } catch (err) {
        if (isInitial && (baseParams.city || baseParams.lat != null)) {
          window.VayuMain.clearStoredLocation();
          window.VayuMain.updateCityBackground("Mumbai");
          try {
            const fallback = await window.VayuApi.getReports({ city: "Mumbai", period });
            window.VayuMain.updateHeaderWeather(fallback);
            renderReportsData(fallback);
            window.VayuMain.showBanner("vmReportsBanner", "VayuMitra supports locations within India only. Showing Mumbai.", "info");
            return;
          } catch (_e) {}
        }
        window.VayuMain.showBanner("vmReportsBanner", err.message || "Unable to load environmental report.", "error");
      }
    }

    segBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        segBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        dateFilter = {
          start_date: "",
          end_date: "",
          compare_city: compareInput ? compareInput.value.trim() : "",
        };
        setInputVal("repStartDate", "");
        setInputVal("repEndDate", "");
        const p = btn.getAttribute("data-period") || "daily";
        loadReports(p, null, false);
      });
    });

    if (dateForm) {
      dateForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const sDate = document.getElementById("repStartDate").value;
        const eDate = document.getElementById("repEndDate").value;
        const cmpCity = compareInput ? compareInput.value.trim() : "";
        dateFilter = {
          start_date: sDate,
          end_date: eDate,
          compare_city: cmpCity,
        };
        const targetPeriod = sDate || eDate ? "custom" : activePeriod;
        loadReports(targetPeriod, null, false);
      });
    }

    if (clearDatesBtn) {
      clearDatesBtn.addEventListener("click", () => {
        dateFilter = { start_date: "", end_date: "", compare_city: "" };
        setInputVal("repStartDate", "");
        setInputVal("repEndDate", "");
        setInputVal("repCompareCityInput", "");
        loadReports("daily", null, false);
      });
    }

    window.addEventListener("vayumitra:citychange", (ev) => {
      const city = ev.detail && ev.detail.city;
      if (city) {
        window.VayuMain.updateCityBackground(city);
        loadReports(activePeriod, { city }, false);
      }
    });

    if (exportBtn) {
      exportBtn.addEventListener("click", () => {
        const params = Object.assign({}, window.VayuMain.getStoredLocationParams(), dateFilter, { period: activePeriod });
        window.location.href = window.VayuApi.getExportCsvUrl(params);
      });
    }

    if (printBtn) {
      printBtn.addEventListener("click", () => window.print());
    }

    await loadReports(activePeriod, null, true);
  }

  function renderReportsData(data) {
    setText("repLocation", data.location ? `${data.location.name} (${data.aqi_standard || "NAQI"})` : "—");
    setText("repGeneratedAt", window.VayuMain.formatDateTime(data.generated_at));

    const cmpSection = document.getElementById("repCompareSection");
    if (cmpSection) {
      if (data.comparison) {
        const cmp = data.comparison;
        cmpSection.classList.remove("vm-hidden");
        setText("repCompareNote", cmp.comparison_note || "");
        setText("repCmpCityName", cmp.location ? cmp.location.name : "—");
        setText("repCmpAvgAqi", `${cmp.average_aqi} (${cmp.average_category})`);
        setText("repCmpRangeAqi", `${cmp.highest_aqi} / ${cmp.lowest_aqi}`);
        setText("repCmpPm25", cmp.average_pm25 != null ? `${cmp.average_pm25} µg/m³` : "N/A");
      } else {
        cmpSection.classList.add("vm-hidden");
      }
    }

    if (!data.sufficient_data || !data.summary) {
      window.VayuMain.showBanner("vmReportsBanner", data.message || "Insufficient historical data to generate report.", "info");
      return;
    }

    const s = data.summary;
    setText("repAvgAqi", `${s.average_aqi} (${s.average_category})`);
    setText("repHighAqi", `${s.highest_aqi}`);
    setText("repLowAqi", `${s.lowest_aqi}`);
    setText("repNetChange", `${s.net_change >= 0 ? "+" : ""}${s.net_change}`);
    setText("repRiskScore", s.risk_score != null ? `${s.risk_score}/100 (${s.risk_level || "--"})` : "--");

    const repRiskBadge = document.getElementById("repRiskBadge");
    if (repRiskBadge) {
      const rLevel = String(s.risk_level || "Moderate Risk");
      const rCls = rLevel.includes("Low")
        ? "vm-status-good"
        : rLevel.includes("Moderate")
        ? "vm-status-moderate"
        : rLevel.includes("Very High")
        ? "vm-status-worse"
        : "vm-status-bad";
      repRiskBadge.className = `vm-status-tag ${rCls}`;
      repRiskBadge.textContent = rLevel;
    }

    const repRiskExplain = document.getElementById("repRiskExplainBox");
    if (repRiskExplain) {
      repRiskExplain.innerHTML = `<strong>Air Risk Score (${s.risk_score ?? "--"}/100 &middot; ${window.VayuMain.escapeHtml(
        s.risk_level || "Evaluating"
      )}):</strong> ${window.VayuMain.escapeHtml(
        s.risk_explanation || "Calculated from average AQI, peak pollution spikes, and hours above AQI 100."
      )}`;
    }

    renderAqiGaugeSvg("vmReportsAvgGauge", s.average_aqi, "AQI (Avg)", s.average_category);

    const topCitiesEl = document.getElementById("repTopCitiesList");
    if (topCitiesEl) {
      const cities = data.top_polluted_cities || [];
      topCitiesEl.innerHTML = cities.length
        ? cities
            .slice(0, 6)
            .map(
              (c, idx) => `
              <div class="vm-rank-item">
                <div style="display:flex; align-items:center; gap:10px; min-width:0;">
                  <span class="vm-rank-num">${idx + 1}</span>
                  <div style="min-width:0;">
                    <strong style="font-size:0.9rem; display:block;">${window.VayuMain.escapeHtml(c.city)} <span style="font-weight:500; color:var(--vm-text-muted); font-size:0.8rem;">&middot; ${window.VayuMain.escapeHtml(c.state)}</span></strong>
                    <span class="vm-meta-line tabular-nums">PM2.5: ${c.pm2_5 ?? "N/A"} &middot; PM10: ${c.pm10 ?? "N/A"} &micro;g/m&sup3;</span>
                  </div>
                </div>
                <span class="vm-status-tag ${levelBadgeClass(c.category)}">AQI ${c.aqi} &middot; ${window.VayuMain.escapeHtml(c.category)}</span>
              </div>
            `
            )
            .join("")
        : `<span class="vm-meta-line">Live city rankings temporarily unavailable.</span>`;
    }

    const hsEl = document.getElementById("repHotspotsList");
    if (hsEl) {
      const hs = data.hotspot_analysis || [];
      hsEl.innerHTML = hs.length
        ? hs
            .map(
              (h, idx) => `
              <div class="vm-rank-item">
                <div style="display:flex; align-items:center; gap:10px; min-width:0;">
                  <span class="vm-rank-num">${idx + 1}</span>
                  <div style="min-width:0;">
                    <strong class="font-mono" style="font-size:0.86rem; display:block;">${window.VayuMain.escapeHtml(h.time.replace("T", " "))}</strong>
                    <span class="vm-meta-line">PM2.5: ${h.pm2_5 ?? "N/A"} · PM10: ${h.pm10 ?? "N/A"} µg/m³</span>
                  </div>
                </div>
                <span class="vm-status-tag ${levelBadgeClass(h.aqi > 200 ? "worse" : h.aqi > 100 ? "bad" : h.aqi > 50 ? "moderate" : "good")}">AQI ${h.aqi}</span>
              </div>
            `
            )
            .join("")
        : `<span class="vm-meta-line">No peak intervals identified.</span>`;
    }

    const series = data.series || [];
    const trendDatasets = [
      {
        label: `${data.location ? data.location.name : "Primary"} (${data.period.toUpperCase()} AQI)`,
        data: series.map((r) => r.aqi),
        borderColor: "#1b8a4b",
        backgroundColor: "rgba(27, 138, 75, 0.14)",
        fill: true,
        tension: 0.3,
      },
    ];
    if (data.comparison && Array.isArray(data.comparison.series) && data.comparison.series.length) {
      const cmpSeries = data.comparison.series;
      trendDatasets.push({
        label: `${data.comparison.location.name} (${data.period.toUpperCase()} AQI)`,
        data: series.map((r, idx) => (cmpSeries[idx] ? cmpSeries[idx].aqi : null)),
        borderColor: "#0ea5e9",
        borderDash: [5, 5],
        fill: false,
        tension: 0.3,
      });
    }
    renderOrReplaceChart("vmReportsTrendChart", {
      type: "line",
      data: {
        labels: series.map((r) => (data.period === "daily" && !data.start_date ? window.VayuMain.formatHourLabel(r.time) : r.date)),
        datasets: trendDatasets,
      },
      options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } },
    });

    const pAvg = s.pollutant_averages || {};
    renderOrReplaceChart("vmReportsPollutantChart", {
      type: "bar",
      data: {
        labels: ["PM2.5", "PM10", "NO2", "SO2", "O3", "CO (x0.1)"],
        datasets: [
          {
            label: "Average Concentration (µg/m³)",
            data: [
              pAvg.pm2_5 || 0,
              pAvg.pm10 || 0,
              pAvg.no2 || 0,
              pAvg.so2 || 0,
              pAvg.o3 || 0,
              pAvg.co ? Number((pAvg.co * 0.1).toFixed(2)) : 0,
            ],
            backgroundColor: ["#16a34a", "#0ea5e9", "#d97706", "#ea580c", "#2563eb", "#64748b"],
            borderRadius: 8,
          },
        ],
      },
      options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } },
    });
  }

  /* =========================================================
     7. MY PERSONAL AIR TWIN & SETTINGS (profile.html)
     ========================================================= */
  let lastProfileBundle = null;

  async function initProfilePage() {
    try {
      const [bundle, twin, authState] = await Promise.all([
        window.VayuApi.getProfile(),
        window.VayuApi.getAirTwin(),
        window.VayuApi.getAuthMe().catch(() => ({ authenticated: false, user: null })),
      ]);
      populateProfileForm(bundle);
      renderAirTwin(twin);
      updateProfileSessionUI(authState, bundle);
    } catch (err) {
      window.VayuMain.showBanner("vmProfileBanner", err.message, "error");
    }

    async function refreshAirTwin() {
      try {
        const twin = await window.VayuApi.getAirTwin();
        renderAirTwin(twin);
      } catch (err) {
        window.VayuMain.showBanner("vmProfileBanner", err.message, "error");
      }
    }

    const locForm = document.getElementById("vmTwinLocationForm");
    if (locForm) {
      locForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          await window.VayuApi.addTwinLocation({
            label: document.getElementById("twinLocLabel").value.trim(),
            city: document.getElementById("twinLocCity").value.trim(),
            hours_per_day: Number((document.getElementById("twinLocHours") || {}).value || 8),
          });
          locForm.reset();
          if (document.getElementById("twinLocHours")) document.getElementById("twinLocHours").value = "8";
          await refreshAirTwin();
          window.VayuMain.showBanner("vmProfileBanner", "Place added to Personal Air Twin.", "success");
        } catch (err) {
          window.VayuMain.showBanner("vmProfileBanner", err.message, "error");
        }
      });
    }

    const actForm = document.getElementById("vmTwinActivityForm");
    if (actForm) {
      actForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const locSel = document.getElementById("twinActLocation");
        try {
          await window.VayuApi.addTwinActivity({
            activity_type: document.getElementById("twinActType").value,
            location_id: locSel && locSel.value ? Number(locSel.value) : null,
            hours_per_day: Number(document.getElementById("twinActHours").value || 1),
            intensity: document.getElementById("twinActIntensity").value,
            is_outdoor: document.getElementById("twinActOutdoor").checked,
          });
          await refreshAirTwin();
          window.VayuMain.showBanner("vmProfileBanner", "Daily activity added.", "success");
        } catch (err) {
          window.VayuMain.showBanner("vmProfileBanner", err.message, "error");
        }
      });
    }

    const diaryForm = document.getElementById("vmTwinDiaryForm");
    if (diaryForm) {
      diaryForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          await window.VayuApi.addTwinDiary({
            notes: document.getElementById("twinDiaryNotes").value.trim(),
          });
          document.getElementById("twinDiaryNotes").value = "";
          await refreshAirTwin();
          window.VayuMain.showBanner("vmProfileBanner", "Exposure diary saved.", "success");
        } catch (err) {
          window.VayuMain.showBanner("vmProfileBanner", err.message, "error");
        }
      });
    }

    const exportBtn = document.getElementById("vmAirTwinExportBtn");
    if (exportBtn) {
      exportBtn.addEventListener("click", () => {
        window.location.href = window.VayuApi.getAirTwinExportUrl();
      });
    }

    const form = document.getElementById("vmProfileSettingsForm");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        window.VayuMain.showBanner("vmProfileBanner", "", "info");

        const prevProf = (lastProfileBundle && lastProfileBundle.profile) || {};
        const prevPref = (lastProfileBundle && lastProfileBundle.preferences) || {};
        const bioEl = document.getElementById("profBio");
        const polUnitEl = document.getElementById("profPollutantUnit");
        const aqiWarnEl = document.getElementById("profAqiWarnings");
        const locAlertEl = document.getElementById("profLocAlerts");
        const notifEnabled = document.getElementById("profNotifEnabled").checked;

        const defaultCity = document.getElementById("profDefaultCity").value.trim() || "Mumbai";
        const payload = {
          profile: {
            name: document.getElementById("profName").value.trim(),
            email: document.getElementById("profEmail").value.trim(),
            bio: bioEl ? bioEl.value.trim() : prevProf.bio || "",
            preferred_city: defaultCity,
          },
          preferences: {
            default_city: defaultCity,
            auto_detect_location: document.getElementById("profAutoDetect").checked,
            temp_unit: document.getElementById("profTempUnit").value,
            pollutant_unit: polUnitEl ? polUnitEl.value : prevPref.pollutant_unit || "ugm3",
            aqi_standard: document.getElementById("profAqiStandard").value,
            share_location: document.getElementById("profShareLocation").checked,
            anonymous_reports: document.getElementById("profAnonReports").checked,
          },
          notifications: {
            enabled: notifEnabled,
            aqi_warnings: aqiWarnEl ? aqiWarnEl.checked : notifEnabled,
            location_alerts: locAlertEl ? locAlertEl.checked : notifEnabled,
            aqi_threshold: Number(document.getElementById("profAqiThreshold").value || 100),
          },
          security: {
            current_password: document.getElementById("profCurrPw").value,
            new_password: document.getElementById("profNewPw").value,
          },
        };

        try {
          const updated = await window.VayuApi.updateProfile(payload);
          window.VayuMain.setStoredCity(updated.preferences.default_city);
          populateProfileForm(updated);
          setInputVal("profCurrPw", "");
          setInputVal("profNewPw", "");
          window.VayuMain.showBanner("vmProfileBanner", "Settings saved.", "success");
          const aq = await window.VayuApi.getAirQuality({ city: updated.preferences.default_city });
          window.VayuMain.updateHeaderWeather(aq);
          await refreshAirTwin();
        } catch (err) {
          window.VayuMain.showBanner("vmProfileBanner", err.message, "error");
        }
      });
    }
  }

  function renderAirTwin(twin) {
    if (!twin) return;
    const sum = twin.daily_summary || {};
    setText(
      "twinWeightedAqi",
      sum.weighted_exposure_aqi != null ? `${sum.weighted_exposure_aqi} (${sum.exposure_category})` : "N/A"
    );
    setText("twinWeightedAqiHero", sum.weighted_exposure_aqi != null ? String(sum.weighted_exposure_aqi) : "N/A");
    setText("twinRiskLabel", sum.exposure_category || "Unavailable");
    setText(
      "twinEstimatedPm25",
      sum.estimated_pm25_exposure != null ? `${sum.estimated_pm25_exposure} µg/m³` : "N/A"
    );
    setText("twinTotalHours", `${sum.total_logged_hours ?? 0} hrs/day`);
    setText("twinOutdoorHours", `${sum.outdoor_hours ?? 0} hrs/day`);

    renderAqiGaugeSvg("vmTwinExposureGauge", sum.weighted_exposure_aqi, "AQI Exposure", sum.exposure_category);

    const locSel = document.getElementById("twinActLocation");
    const locs = twin.locations || [];
    if (locSel) {
      locSel.innerHTML =
        `<option value="">Default (${window.VayuMain.escapeHtml(twin.preferred_city)})</option>` +
        locs.map((l) => `<option value="${l.id}">${window.VayuMain.escapeHtml(l.label)} (${window.VayuMain.escapeHtml(l.city)})</option>`).join("");
    }

    const locsEl = document.getElementById("vmTwinLocationsList");
    if (locsEl) {
      if (!locs.length) {
        locsEl.innerHTML = `<div class="vm-twin-item-row"><span>No custom places added yet (${window.VayuMain.escapeHtml(twin.preferred_city)}).</span></div>`;
      } else {
        locsEl.innerHTML = locs
          .map(
            (l) => `
            <div class="vm-twin-item-row">
              <div>
                <strong>${window.VayuMain.escapeHtml(l.label)}</strong> · ${window.VayuMain.escapeHtml(l.city)} (${l.hours_per_day ?? 8}h/day)
                <div class="vm-meta-line tabular-nums">Live AQI: ${l.live_aqi ?? "N/A"} (${window.VayuMain.escapeHtml(l.category)}) · PM2.5: ${l.live_pm25 ?? "N/A"} µg/m³</div>
              </div>
              <button type="button" class="vm-btn vm-btn-outline vm-btn-sm vm-del-loc-btn" data-id="${l.id}">Remove</button>
            </div>
          `
          )
          .join("");
        locsEl.querySelectorAll(".vm-del-loc-btn").forEach((btn) => {
          btn.addEventListener("click", async () => {
            await window.VayuApi.deleteTwinLocation(Number(btn.getAttribute("data-id")));
            const fresh = await window.VayuApi.getAirTwin();
            renderAirTwin(fresh);
          });
        });
      }
    }

    const actsEl = document.getElementById("vmTwinActivitiesList");
    const acts = twin.activities || [];
    if (actsEl) {
      if (!acts.length) {
        actsEl.innerHTML = `<div class="vm-twin-item-row"><span>No daily activities logged yet.</span></div>`;
      } else {
        actsEl.innerHTML = acts
          .map(
            (a) => `
            <div class="vm-twin-item-row">
              <div>
                <strong>${window.VayuMain.escapeHtml(a.activity_type)}</strong> · ${a.hours_per_day}h/day · ${a.is_outdoor ? "Outdoor" : "Indoor"} (${window.VayuMain.escapeHtml(a.intensity)})
                <div class="vm-meta-line tabular-nums">Place: ${window.VayuMain.escapeHtml(a.location_label)} · Exposure AQI: <strong>${a.calculated_exposure_aqi ?? "N/A"}</strong></div>
              </div>
              <button type="button" class="vm-btn vm-btn-outline vm-btn-sm vm-del-act-btn" data-id="${a.id}">Remove</button>
            </div>
          `
          )
          .join("");
        actsEl.querySelectorAll(".vm-del-act-btn").forEach((btn) => {
          btn.addEventListener("click", async () => {
            await window.VayuApi.deleteTwinActivity(Number(btn.getAttribute("data-id")));
            const fresh = await window.VayuApi.getAirTwin();
            renderAirTwin(fresh);
          });
        });
      }
    }

    const diaryEl = document.getElementById("vmTwinDiaryList");
    const diary = twin.diary || [];
    if (diaryEl) {
      diaryEl.innerHTML = diary.length
        ? diary
            .slice(0, 8)
            .map(
              (d) => `
              <li>
                <div class="vm-aqi-header-row" style="margin-bottom:4px;">
                  <strong class="font-mono">${window.VayuMain.escapeHtml(d.entry_date)} · ${window.VayuMain.escapeHtml(d.city)}</strong>
                  <span class="vm-status-tag ${levelBadgeClass(d.estimated_aqi > 200 ? "worse" : d.estimated_aqi > 100 ? "bad" : d.estimated_aqi > 50 ? "moderate" : "good")}">Est. AQI ${d.estimated_aqi}</span>
                </div>
                <p class="vm-section-subtitle">${window.VayuMain.escapeHtml(d.activity_summary)}${d.notes ? ` · "${window.VayuMain.escapeHtml(d.notes)}"` : ""}</p>
              </li>
            `
            )
            .join("")
        : "<li>No diary entries yet.</li>";
    }

    const weeklyTrend = twin.weekly_exposure_trend || [];
    const chartEntries = diary.slice().reverse();
    renderOrReplaceChart("vmTwinExposureChart", {
      type: "line",
      data: {
        labels: weeklyTrend.length
          ? weeklyTrend.map((w) => w.date)
          : chartEntries.length
          ? chartEntries.map((d) => d.entry_date)
          : ["Today"],
        datasets: [
          {
            label: `Weekly Exposure (${twin.aqi_standard || "NAQI"})`,
            data: weeklyTrend.length
              ? weeklyTrend.map((w) => w.exposure_aqi)
              : chartEntries.length
              ? chartEntries.map((d) => d.estimated_aqi)
              : [sum.weighted_exposure_aqi || 0],
            borderColor: "#1b8a4b",
            backgroundColor: "rgba(27, 138, 75, 0.16)",
            fill: true,
            tension: 0.32,
          },
        ],
      },
      options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } },
    });

    const locCmp = twin.location_comparison || [];
    renderOrReplaceChart("vmTwinLocCompareChart", {
      type: "bar",
      data: {
        labels: locCmp.length ? locCmp.map((l) => l.label) : [twin.preferred_city || "Default"],
        datasets: [
          {
            label: `Ambient AQI (${twin.aqi_standard || "NAQI"})`,
            data: locCmp.length ? locCmp.map((l) => l.live_aqi || 0) : [0],
            backgroundColor: locCmp.map((l) => aqiColorHex(l.live_aqi || 0)),
            borderRadius: 8,
          },
        ],
      },
      options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } },
    });
  }

  function populateProfileForm(bundle) {
    lastProfileBundle = bundle;
    const p = bundle.profile || {};
    const pr = bundle.preferences || {};
    const n = bundle.notifications || {};

    const displayName = (p.name || "VayuMitra User").trim();
    setText("profAvatarBadge", (displayName.charAt(0) || "V").toUpperCase());
    setText("profHeroName", displayName);
    setText("profHeroCityPill", `Default City: ${pr.default_city || p.preferred_city || "Mumbai"}`);
    setText("profGoalThreshold", String(n.aqi_threshold || 100));
    setText("profGoalNotifs", n.enabled ? "Enabled" : "Disabled");
    setText("profGoalStd", pr.aqi_standard || "NAQI");

    setInputVal("profName", p.name);
    setInputVal("profEmail", p.email);
    setInputVal("profDefaultCity", pr.default_city || p.preferred_city);
    setCheck("profAutoDetect", pr.auto_detect_location);
    setInputVal("profTempUnit", pr.temp_unit || "C");
    setInputVal("profAqiStandard", pr.aqi_standard || "NAQI");
    setCheck("profShareLocation", pr.share_location);
    setCheck("profAnonReports", pr.anonymous_reports);
    setCheck("profNotifEnabled", n.enabled);
    setInputVal("profAqiThreshold", n.aqi_threshold || 100);
    setText("profSecurityStatus", p.has_password ? "Password protection is active." : "No password set.");
  }

  function updateProfileSessionUI(authState, bundle) {
    const statusEl = document.getElementById("profSessionStatus");
    const switchBtn = document.getElementById("vmSettingsSwitchAccountBtn");
    const logoutBtn = document.getElementById("vmSettingsLogoutLink");
    const isAuth = Boolean(authState && authState.authenticated && authState.user);
    if (isAuth) {
      const u = authState.user;
      window.VayuMain.setAuthSession(window.VayuMain.getAuthToken(), u);
      if (statusEl) {
        statusEl.textContent = `Signed in as ${u.name || "Citizen"} (${u.email || ""})`;
      }
      if (switchBtn) switchBtn.textContent = "Switch Account";
      if (logoutBtn) logoutBtn.classList.remove("vm-hidden");
    } else {
      window.VayuMain.clearAuthSession();
      const profName = (bundle && bundle.profile && bundle.profile.name) || "Guest";
      if (statusEl) {
        statusEl.textContent = `Signed out (viewing ${profName} defaults). Sign in to sync your personal account or visit the Logout page.`;
      }
      if (switchBtn) switchBtn.textContent = "Sign In";
    }
  }

  /* =========================================================
     8. LOGIN & LOGOUT PAGES (login.html & logout.html)
     ========================================================= */
  function initLoginPage() {
    const tabLogin = document.getElementById("vmTabLoginBtn");
    const tabReg = document.getElementById("vmTabRegisterBtn");
    const loginForm = document.getElementById("vmLoginForm");
    const regForm = document.getElementById("vmRegisterForm");
    const fillDemoBtn = document.getElementById("vmFillDemoBtn");
    const nextUrl = new URLSearchParams(window.location.search).get("next") || "index.html";

    function switchTab(mode) {
      const isLogin = mode === "login";
      if (tabLogin) {
        tabLogin.classList.toggle("active", isLogin);
        tabLogin.setAttribute("aria-selected", String(isLogin));
      }
      if (tabReg) {
        tabReg.classList.toggle("active", !isLogin);
        tabReg.setAttribute("aria-selected", String(!isLogin));
      }
      if (loginForm) loginForm.classList.toggle("vm-hidden", !isLogin);
      if (regForm) regForm.classList.toggle("vm-hidden", isLogin);
      window.VayuMain.showBanner("vmLoginBanner", "", "info");
    }

    if (tabLogin) tabLogin.addEventListener("click", () => switchTab("login"));
    if (tabReg) tabReg.addEventListener("click", () => switchTab("register"));

    [
      ["loginTogglePw", "loginPassword"],
      ["regTogglePw", "regPassword"],
    ].forEach(([btnId, inputId]) => {
      const btn = document.getElementById(btnId);
      const inp = document.getElementById(inputId);
      if (btn && inp) {
        btn.addEventListener("click", () => {
          const isPw = inp.getAttribute("type") === "password";
          inp.setAttribute("type", isPw ? "text" : "password");
          btn.setAttribute("aria-label", isPw ? "Hide password" : "Show password");
        });
      }
    });

    if (fillDemoBtn) {
      fillDemoBtn.addEventListener("click", () => {
        setInputVal("loginEmail", "aarav@vayumitra.in");
        setInputVal("loginPassword", "vayumitra123");
      });
    }

    if (loginForm) {
      loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = document.getElementById("vmLoginSubmitBtn");
        if (btn) btn.disabled = true;
        window.VayuMain.showBanner("vmLoginBanner", "", "info");
        try {
          const res = await window.VayuApi.login({
            email: (document.getElementById("loginEmail") || {}).value || "",
            password: (document.getElementById("loginPassword") || {}).value || "",
          });
          window.VayuMain.setAuthSession(res.token, res.user);
          if (res.user && res.user.preferred_city) {
            window.VayuMain.setStoredCity(res.user.preferred_city);
          }
          window.VayuMain.showBanner("vmLoginBanner", res.message || "Signed in! Redirecting...", "success");
          setTimeout(() => {
            window.location.href = nextUrl;
          }, 550);
        } catch (err) {
          window.VayuMain.showBanner("vmLoginBanner", err.message || "Login failed.", "error");
        } finally {
          if (btn) btn.disabled = false;
        }
      });
    }

    if (regForm) {
      regForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = document.getElementById("vmRegisterSubmitBtn");
        if (btn) btn.disabled = true;
        window.VayuMain.showBanner("vmLoginBanner", "", "info");
        try {
          const res = await window.VayuApi.register({
            name: (document.getElementById("regName") || {}).value || "",
            email: (document.getElementById("regEmail") || {}).value || "",
            preferred_city: (document.getElementById("regPreferredCity") || {}).value || "Mumbai",
            password: (document.getElementById("regPassword") || {}).value || "",
          });
          window.VayuMain.setAuthSession(res.token, res.user);
          if (res.user && res.user.preferred_city) {
            window.VayuMain.setStoredCity(res.user.preferred_city);
          }
          window.VayuMain.showBanner("vmLoginBanner", res.message || "Account created! Redirecting...", "success");
          setTimeout(() => {
            window.location.href = nextUrl;
          }, 550);
        } catch (err) {
          window.VayuMain.showBanner("vmLoginBanner", err.message || "Registration failed.", "error");
        } finally {
          if (btn) btn.disabled = false;
        }
      });
    }
  }

  async function initLogoutPage() {
    const prevUser = window.VayuMain.getAuthUser();
    const hadToken = Boolean(window.VayuMain.getAuthToken());
    try {
      await window.VayuApi.logout();
    } catch (_e) {}
    window.VayuMain.clearAuthSession();

    const navAuthBtn = document.getElementById("vmNavAuthBtn");
    if (navAuthBtn) {
      navAuthBtn.href = "login.html";
      navAuthBtn.className = "vm-nav-auth-chip";
      navAuthBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path><polyline points="10 17 15 12 10 7"></polyline><line x1="15" y1="12" x2="3" y2="12"></line></svg><span>Login</span>`;
    }

    setText("vmLogoutTitle", hadToken ? "You have been logged out" : "Logged out cleanly");
    setText(
      "vmLogoutDesc",
      hadToken
        ? "Your VayuMitra session has been ended safely on this device."
        : "No active session remains on this device. You can sign in below anytime."
    );

    const infoBox = document.getElementById("vmLogoutAccountInfo");
    if (infoBox && prevUser && prevUser.name) {
      infoBox.classList.remove("vm-hidden");
      infoBox.innerHTML = `<strong>Signed out from:</strong> ${window.VayuMain.escapeHtml(prevUser.name)}${
        prevUser.email ? ` (${window.VayuMain.escapeHtml(prevUser.email)})` : ""
      }`;
    }
  }

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text == null ? "" : String(text);
  }
  function setInputVal(id, val) {
    const el = document.getElementById(id);
    if (el) el.value = val == null ? "" : String(val);
  }
  function setCheck(id, val) {
    const el = document.getElementById(id);
    if (el) el.checked = Boolean(val);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const page = document.body.getAttribute("data-page");
    if (page === "dashboard") initDashboardPage();
    else if (page === "insights") initInsightsPage();
    else if (page === "routes") initRoutesPage();
    else if (page === "community") initCommunityPage();
    else if (page === "alerts") initAlertsPage();
    else if (page === "reports") initReportsPage();
    else if (page === "profile") initProfilePage();
    else if (page === "login") initLoginPage();
    else if (page === "logout") initLogoutPage();
  });
})(window, document);
