(function () {
  "use strict";

  const DATA_URL = "../../data/treasury-securities-net-issuance.json";
  const METADATA_URL = "../../data/treasury-securities-net-issuance-metadata.json";
  const SP500_DATA_URL = "../../data/sp500.json";
  const SP500_METADATA_URL = "../../data/sp500-metadata.json";
  const DEFAULT_FREQUENCY = "ME";
  const SHARE_STATE_VERSION = "1";
  const USD_BILLION = 1000000000;
  const SECURITY_ORDER = ["Bill", "Note", "Bond"];
  const FREQUENCY_LABELS = {
    D: "Daily",
    W: "Weekly",
    ME: "Month End",
    QE: "Quarter End",
    YE: "Year End"
  };
  const SECURITY_COLORS = {
    Bill: "#1f5fbf",
    Note: "#16865a",
    Bond: "#c33a2b"
  };
  const SP500_LINE_COLOR = "#293241";
  const FILTER_DEBOUNCE_MS = 80;
  const COPY_FEEDBACK_MS = 2200;

  let metadata = null;
  let sp500Metadata = null;
  let rows = [];
  let sp500Rows = [];
  let columnIndex = {};
  let sp500ColumnIndex = {};
  let securityTypes = [];
  let sp500Error = null;
  let applyTimer = null;
  let renderSequence = 0;
  let pendingAxisRanges = null;
  let copyFeedbackTimer = null;
  let copyFeedbackTargets = [];
  const timings = {
    fetch: null,
    parse: null,
    filter: null,
    trace: null,
    render: null
  };
  const sp500Timings = {
    fetch: null,
    parse: null
  };

  function element(id) {
    return window.MacroObservatory.getElement(id);
  }

  function setText(id, value) {
    window.MacroObservatory.setText(id, value);
  }

  function formatMs(value) {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return "-";
    }
    if (value < 1000) {
      return `${Math.round(value)} ms`;
    }
    return `${(value / 1000).toFixed(2)} s`;
  }

  function formatFrequency(value) {
    return FREQUENCY_LABELS[value] || value;
  }

  function todayIsoDate() {
    const now = new Date();
    const localDate = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
    return localDate.toISOString().slice(0, 10);
  }

  function toBillions(value) {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return null;
    }
    return value / USD_BILLION;
  }

  function requiredColumn(name) {
    if (!(name in columnIndex)) {
      throw new Error(`Treasury securities data is missing required column: ${name}`);
    }
    return columnIndex[name];
  }

  function rowValue(row, columnName) {
    return row[requiredColumn(columnName)];
  }

  function requiredSp500Column(name) {
    if (!(name in sp500ColumnIndex)) {
      throw new Error(`SP500 data is missing required column: ${name}`);
    }
    return sp500ColumnIndex[name];
  }

  function numericSp500Value(row, columnName) {
    const rawValue = row[requiredSp500Column(columnName)];
    if (rawValue === null || rawValue === undefined || rawValue === "" || rawValue === ".") {
      return null;
    }
    const value = Number(rawValue);
    return Number.isFinite(value) ? value : null;
  }

  function numericRowValue(row, columnName) {
    const value = Number(rowValue(row, columnName));
    return Number.isFinite(value) ? value : null;
  }

  function orderedSecurityTypes(values) {
    const order = new Map(SECURITY_ORDER.map((value, index) => [value, index]));
    return Array.from(values).sort((left, right) => {
      const leftRank = order.has(left) ? order.get(left) : SECURITY_ORDER.length;
      const rightRank = order.has(right) ? order.get(right) : SECURITY_ORDER.length;
      if (leftRank !== rightRank) {
        return leftRank - rightRank;
      }
      return left.localeCompare(right);
    });
  }

  function canonicalSecurityTypes(rawTypes) {
    const byLower = new Map(securityTypes.map((value) => [value.toLowerCase(), value]));
    const selected = new Set();
    rawTypes.forEach((rawType) => {
      const key = String(rawType || "").trim().toLowerCase();
      if (byLower.has(key)) {
        selected.add(byLower.get(key));
      }
    });
    return orderedSecurityTypes(selected);
  }

  function sourceRows(metadataPayload) {
    return metadataPayload.source_rows || {};
  }

  function sp500Available() {
    return sp500Metadata !== null && sp500Rows.length > 0 && sp500Error === null;
  }

  function latestSp500Row() {
    if (sp500Rows.length === 0) {
      return null;
    }
    return sp500Rows[sp500Rows.length - 1];
  }

  function renderSp500Status() {
    const status = element("sp500-overlay-status");
    const ui = controls();
    if (sp500Error !== null) {
      status.hidden = false;
      status.textContent = "S&P 500 unavailable";
      return;
    }
    if (!ui.sp500Overlay.checked) {
      status.hidden = true;
      status.textContent = "";
      return;
    }
    const latest = latestSp500Row();
    const seriesId = sp500Metadata && sp500Metadata.series_id ? sp500Metadata.series_id : "SP500";
    status.hidden = false;
    status.textContent = `S&P 500: FRED ${seriesId}, latest ${window.MacroObservatory.formatDate(latest ? latest.date : null)}`;
  }

  function renderSourceRows() {
    const list = element("source-row-list");
    window.MacroObservatory.clearChildren(list);
    Object.keys(sourceRows(metadata))
      .sort()
      .forEach((key) => {
        const row = document.createElement("div");
        row.className = "source-row-item";

        const name = document.createElement("span");
        name.className = "source-row-key";
        name.textContent = key;

        const value = document.createElement("span");
        value.className = "source-row-value";
        value.textContent = window.MacroObservatory.formatInteger(sourceRows(metadata)[key]);

        row.appendChild(name);
        row.appendChild(value);
        list.appendChild(row);
      });
  }

  function renderMetadata() {
    const dateRange = metadata.date_range || {};
    setText("dataset-summary", metadata.title || "Treasury securities net issuance dataset");
    setText("built-at", window.MacroObservatory.formatIsoDateTime(metadata.dataset_built_at));
    setText("metric-today", todayIsoDate());
    setText("metric-row-count", window.MacroObservatory.formatInteger(metadata.row_count));
    setText("metric-chart-points", "Loading");
    setText("metric-frequency", formatFrequency(metadata.default_frequency || DEFAULT_FREQUENCY));
    setText("metadata-units", metadata.display_units || "n/a");
    setText("metadata-formula", metadata.formula || "net_issuance = issued - maturing");
    setText("metadata-policy", metadata.future_maturity_policy || metadata.date_policy || "n/a");
    setText(
      "filtered-range-label",
      `${window.MacroObservatory.formatDate(dateRange.min)} to ${window.MacroObservatory.formatDate(dateRange.max)}`
    );
    renderSourceRows();
  }

  function renderFrequencyOptions() {
    const select = element("frequency-select");
    window.MacroObservatory.clearChildren(select);
    const frequencies = metadata.frequencies && metadata.frequencies.length > 0
      ? metadata.frequencies
      : ["D", "W", "ME", "QE", "YE"];
    frequencies.forEach((frequency) => {
      const option = document.createElement("option");
      option.value = frequency;
      option.textContent = formatFrequency(frequency);
      select.appendChild(option);
    });
    select.value = metadata.default_frequency || DEFAULT_FREQUENCY;
  }

  function renderSecurityTypeControls() {
    const list = element("security-type-list");
    window.MacroObservatory.clearChildren(list);
    securityTypes.forEach((securityType) => {
      const id = `security-type-${securityType.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
      const label = document.createElement("label");
      label.className = "checkbox-row";
      label.setAttribute("for", id);

      const checkbox = document.createElement("input");
      checkbox.id = id;
      checkbox.type = "checkbox";
      checkbox.value = securityType;
      checkbox.checked = true;
      checkbox.dataset.securityType = securityType;

      const text = document.createElement("span");
      text.textContent = securityType;

      label.appendChild(checkbox);
      label.appendChild(text);
      list.appendChild(label);
    });
  }

  function controls() {
    return {
      frequency: element("frequency-select"),
      reset: element("reset-button"),
      copyLink: element("treasury-securities-copy-link"),
      cumulative: element("cumulative-toggle"),
      sp500Overlay: element("sp500-overlay-toggle"),
      securityTypeInputs: Array.from(
        element("security-type-list").querySelectorAll("input[type='checkbox']")
      )
    };
  }

  function selectedSecurityTypeList(ui) {
    return orderedSecurityTypes(
      ui.securityTypeInputs
        .filter((input) => input.checked)
        .map((input) => input.dataset.securityType)
    );
  }

  function selectedSecurityTypes(ui) {
    return new Set(selectedSecurityTypeList(ui));
  }

  function resetControls() {
    const ui = controls();
    ui.frequency.value = metadata.default_frequency || DEFAULT_FREQUENCY;
    ui.securityTypeInputs.forEach((input) => {
      input.checked = true;
    });
    ui.cumulative.checked = false;
    ui.sp500Overlay.checked = false;
  }

  function validAxisText(value) {
    if (value === null || value === undefined) {
      return null;
    }
    const text = String(value).trim();
    if (!text || text.length > 80 || /[<>\n\r]/.test(text)) {
      return null;
    }
    return text;
  }

  function validXAxisText(value) {
    const text = validAxisText(value);
    if (text === null) {
      return null;
    }
    return Number.isNaN(Date.parse(text)) ? null : text;
  }

  function validAxisNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  }

  function parseSharedState() {
    if (!window.location.hash || window.location.hash.length <= 1) {
      return null;
    }

    try {
      const params = new URLSearchParams(window.location.hash.slice(1));
      if (params.get("v") !== SHARE_STATE_VERSION) {
        return null;
      }

      const state = {
        frequency: validAxisText(params.get("freq")),
        rawTypes: null,
        hasTypes: params.has("types"),
        cumulative: params.get("cum") === "1",
        showSp500: params.get("sp500") === "1",
        axisRanges: {}
      };

      if (state.hasTypes) {
        const rawTypes = params.get("types") || "";
        state.rawTypes = rawTypes === "" ? [] : rawTypes.split(",");
      }

      const x0 = validXAxisText(params.get("x0"));
      const x1 = validXAxisText(params.get("x1"));
      if (x0 !== null && x1 !== null && x0 !== x1) {
        state.axisRanges.x = [x0, x1];
      }

      const y0 = validAxisNumber(params.get("y0"));
      const y1 = validAxisNumber(params.get("y1"));
      if (y0 !== null && y1 !== null && y0 !== y1) {
        state.axisRanges.y = [y0, y1];
      }

      const sp500Y0 = validAxisNumber(params.get("sp500y0"));
      const sp500Y1 = validAxisNumber(params.get("sp500y1"));
      if (state.showSp500 && sp500Y0 !== null && sp500Y1 !== null && sp500Y0 !== sp500Y1) {
        state.axisRanges.y2 = [sp500Y0, sp500Y1];
      }

      return state;
    } catch (_error) {
      return null;
    }
  }

  function applySharedControlState(state) {
    if (!state) {
      return;
    }

    const ui = controls();
    const allowedFrequencies = new Set(Array.from(ui.frequency.options).map((option) => option.value));
    if (state.frequency && allowedFrequencies.has(state.frequency)) {
      ui.frequency.value = state.frequency;
    }

    if (state.hasTypes) {
      const validTypes = canonicalSecurityTypes(state.rawTypes || []);
      if ((state.rawTypes || []).length === 0 || validTypes.length > 0) {
        const validTypeSet = new Set(validTypes);
        ui.securityTypeInputs.forEach((input) => {
          input.checked = validTypeSet.has(input.dataset.securityType);
        });
      }
    }

    if (state.cumulative) {
      ui.cumulative.checked = true;
    }

    if (state.showSp500 && sp500Available()) {
      ui.sp500Overlay.checked = true;
    }

    if (
      state.axisRanges
      && (
        Array.isArray(state.axisRanges.x)
        || Array.isArray(state.axisRanges.y)
        || Array.isArray(state.axisRanges.y2)
      )
    ) {
      pendingAxisRanges = state.axisRanges;
    }
  }

  function filterRows() {
    const ui = controls();
    const started = performance.now();
    const frequency = ui.frequency.value;
    const selectedTypes = selectedSecurityTypes(ui);
    const selectedTypeList = selectedSecurityTypeList(ui);
    const filtered = [];
    let minDate = null;
    let maxDate = null;

    for (let index = 0; index < rows.length; index += 1) {
      const row = rows[index];
      if (rowValue(row, "frequency") !== frequency) {
        continue;
      }
      const securityType = String(rowValue(row, "security_type") || "");
      if (!selectedTypes.has(securityType)) {
        continue;
      }
      const netIssuance = numericRowValue(row, "net_issuance");
      if (netIssuance === null || netIssuance === 0) {
        continue;
      }
      const date = rowValue(row, "date");
      filtered.push(row);
      if (minDate === null || date < minDate) {
        minDate = date;
      }
      if (maxDate === null || date > maxDate) {
        maxDate = date;
      }
    }

    timings.filter = performance.now() - started;
    return {
      frequency,
      rows: filtered,
      minDate,
      maxDate,
      selectedTypeList,
      cumulative: ui.cumulative.checked,
      showSp500: ui.sp500Overlay.checked && sp500Available()
    };
  }

  function renderDiagnostics(pointCount) {
    const parts = [
      `Rows ${window.MacroObservatory.formatInteger(pointCount)}`,
      `Data ${formatMs(timings.fetch)}`,
      `Parse ${formatMs(timings.parse)}`,
      `Filter ${formatMs(timings.filter)}`,
      `Trace ${formatMs(timings.trace)}`,
      `Render ${formatMs(timings.render)}`
    ];
    if (sp500Available() && controls().sp500Overlay.checked) {
      parts.splice(3, 0, `SP500 ${formatMs((sp500Timings.fetch || 0) + (sp500Timings.parse || 0))}`);
    }
    element("diagnostics-bar").textContent = parts.join(" | ");
  }

  function showGuardrail(message) {
    const guardrail = element("guardrail-message");
    guardrail.textContent = message;
    guardrail.hidden = false;
  }

  function hideGuardrail() {
    element("guardrail-message").hidden = true;
  }

  function purgeChart() {
    if (window.Plotly) {
      window.Plotly.purge("treasury-securities-chart");
    }
  }

  function selectedTypeLabel(selectedTypeList) {
    if (selectedTypeList.length === 0) {
      return "No security types";
    }
    if (selectedTypeList.length === securityTypes.length) {
      return "All security types";
    }
    return selectedTypeList.join(", ");
  }

  function updateFilterSummary(filtered) {
    const range = metadata.date_range || {};
    const labelMin = filtered.minDate || range.min;
    const labelMax = filtered.maxDate || range.max;
    const pointCount = filtered.rows.length;
    setText("metric-chart-points", window.MacroObservatory.formatInteger(pointCount));
    setText("metric-frequency", formatFrequency(filtered.frequency));
    setText("control-point-count", `${window.MacroObservatory.formatInteger(pointCount)} points`);
    const cumulativeLabel = filtered.cumulative ? ", cumulative" : "";
    const overlayLabel = filtered.showSp500 ? ", S&P 500 overlay" : "";
    setText("chart-heading", filtered.cumulative ? "Cumulative Net Issuance" : "Net Issuance");
    setText(
      "filtered-range-label",
      `${formatFrequency(filtered.frequency)}${cumulativeLabel}, ${selectedTypeLabel(filtered.selectedTypeList)}, ${window.MacroObservatory.formatInteger(pointCount)} non-zero points, ${window.MacroObservatory.formatDate(labelMin)} to ${window.MacroObservatory.formatDate(labelMax)}${overlayLabel}`
    );
    renderSp500Status();
  }

  function buildSp500Trace() {
    return {
      x: sp500Rows.map((row) => row.date),
      y: sp500Rows.map((row) => row.value),
      name: "S&P 500",
      type: "scatter",
      mode: "lines",
      yaxis: "y2",
      line: {
        color: SP500_LINE_COLOR,
        width: 2
      },
      hovertemplate: [
        "S&P 500",
        "%{x}",
        "Close: %{y:,.2f}<extra></extra>"
      ].join("<br>")
    };
  }

  function buildTraces(filtered) {
    const started = performance.now();
    const grouped = new Map();
    filtered.rows.forEach((row) => {
      const securityType = String(rowValue(row, "security_type") || "Unknown");
      let group = grouped.get(securityType);
      if (!group) {
        group = [];
        grouped.set(securityType, group);
      }
      group.push(row);
    });

    const traces = orderedSecurityTypes(grouped.keys()).map((securityType) => {
      const groupRows = grouped.get(securityType).slice().sort((left, right) => {
        return String(rowValue(left, "date")).localeCompare(String(rowValue(right, "date")));
      });
      const group = { x: [], y: [], customdata: [] };
      let cumulativeNetIssuance = 0;
      groupRows.forEach((row) => {
        const netIssuance = numericRowValue(row, "net_issuance");
        if (netIssuance === null) {
          return;
        }
        cumulativeNetIssuance += netIssuance;
        group.x.push(rowValue(row, "date"));
        group.y.push(toBillions(filtered.cumulative ? cumulativeNetIssuance : netIssuance));
        group.customdata.push([
          toBillions(numericRowValue(row, "issued")),
          toBillions(numericRowValue(row, "maturing")),
          toBillions(netIssuance)
        ]);
      });
      return {
        x: group.x,
        y: group.y,
        customdata: group.customdata,
        name: securityType,
        type: "bar",
        showlegend: true,
        marker: {
          color: SECURITY_COLORS[securityType] || "#6d45a8",
          line: {
            color: "rgba(255, 255, 255, 0.45)",
            width: 0.4
          }
        },
        hovertemplate: filtered.cumulative
          ? [
            "%{fullData.name}",
            "%{x}",
            "Cumulative net issuance: %{y:$,.1f}B",
            "Period net issuance: %{customdata[2]:$,.1f}B",
            "Issued: %{customdata[0]:$,.1f}B",
            "Maturing: %{customdata[1]:$,.1f}B<extra></extra>"
          ].join("<br>")
          : [
            "%{fullData.name}",
            "%{x}",
            "Net issuance: %{y:$,.1f}B",
            "Issued: %{customdata[0]:$,.1f}B",
            "Maturing: %{customdata[1]:$,.1f}B<extra></extra>"
          ].join("<br>")
      };
    });

    if (filtered.showSp500) {
      traces.push(buildSp500Trace());
    }

    timings.trace = performance.now() - started;
    return traces;
  }

  function todayMarker(filtered) {
    const today = todayIsoDate();
    const range = metadata.date_range || {};
    const minDate = filtered.minDate || range.min;
    const maxDate = filtered.maxDate || range.max;
    if (!minDate || !maxDate || today < minDate || today > maxDate) {
      return { shapes: [], annotations: [] };
    }
    return {
      shapes: [
        {
          type: "line",
          xref: "x",
          yref: "paper",
          x0: today,
          x1: today,
          y0: 0,
          y1: 1,
          line: {
            color: "#637083",
            width: 1.4,
            dash: "dot"
          }
        }
      ],
      annotations: [
        {
          text: "Today",
          x: today,
          xref: "x",
          y: 1.03,
          yref: "paper",
          showarrow: false,
          font: { size: 12, color: "#637083" },
          bgcolor: "rgba(255,255,255,0.88)",
          bordercolor: "#d7dde7",
          borderwidth: 1,
          borderpad: 3
        }
      ]
    };
  }

  function chartLayout(filtered) {
    const marker = todayMarker(filtered);
    const layout = {
      autosize: true,
      barmode: "relative",
      bargap: filtered.frequency === "D" ? 0.04 : 0.08,
      margin: { t: 32, r: filtered.showSp500 ? 86 : 28, b: 60, l: 72 },
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#ffffff",
      font: {
        family: "Inter, Segoe UI, sans-serif",
        color: "#172033"
      },
      showlegend: true,
      legend: {
        orientation: "h",
        y: 1.08,
        x: 0,
        font: { size: 12 }
      },
      xaxis: {
        title: "",
        showgrid: true,
        gridcolor: "#e7ebf1",
        rangeselector: {
          x: 0,
          y: 1.16,
          bgcolor: "#ffffff",
          activecolor: "#dbe8ff",
          bordercolor: "#d7dde7",
          borderwidth: 1,
          buttons: [
            { count: 1, label: "1Y", step: "year", stepmode: "backward" },
            { count: 5, label: "5Y", step: "year", stepmode: "backward" },
            { count: 10, label: "10Y", step: "year", stepmode: "backward" },
            { step: "all", label: "All" }
          ]
        }
      },
      yaxis: {
        title: filtered.cumulative ? "Cumulative net issuance, USD billions" : "Net issuance, USD billions",
        showgrid: true,
        gridcolor: "#e7ebf1",
        zerolinecolor: "#aab4c2",
        tickprefix: "$",
        ticksuffix: "B",
        tickformat: ",.0f"
      },
      yaxis2: filtered.showSp500
        ? {
          title: "S&P 500, index points",
          overlaying: "y",
          side: "right",
          showgrid: false,
          zeroline: false,
          tickformat: ",.0f"
        }
        : { visible: false },
      hovermode: "x unified",
      shapes: marker.shapes,
      annotations: marker.annotations
    };
    return layout;
  }

  function chartConfig() {
    return {
      displaylogo: false,
      responsive: true
    };
  }

  async function applyPendingAxisRanges() {
    if (!pendingAxisRanges || !window.Plotly) {
      pendingAxisRanges = null;
      return;
    }

    const update = {};
    if (Array.isArray(pendingAxisRanges.x)) {
      update["xaxis.range[0]"] = pendingAxisRanges.x[0];
      update["xaxis.range[1]"] = pendingAxisRanges.x[1];
    }
    if (Array.isArray(pendingAxisRanges.y)) {
      update["yaxis.range[0]"] = pendingAxisRanges.y[0];
      update["yaxis.range[1]"] = pendingAxisRanges.y[1];
    }
    if (Array.isArray(pendingAxisRanges.y2) && controls().sp500Overlay.checked) {
      update["yaxis2.range[0]"] = pendingAxisRanges.y2[0];
      update["yaxis2.range[1]"] = pendingAxisRanges.y2[1];
    }
    pendingAxisRanges = null;

    if (Object.keys(update).length > 0) {
      await window.Plotly.relayout("treasury-securities-chart", update);
    }
  }

  async function renderChart(filtered, sequence) {
    if (!window.Plotly) {
      throw new Error("Plotly did not load. Check the CDN connection and reload the page.");
    }
    const traces = buildTraces(filtered);
    if (sequence !== renderSequence) {
      return;
    }
    const renderStarted = performance.now();
    await window.Plotly.react(
      "treasury-securities-chart",
      traces,
      chartLayout(filtered),
      chartConfig()
    );
    if (sequence !== renderSequence) {
      return;
    }
    await applyPendingAxisRanges();
    if (sequence !== renderSequence) {
      return;
    }
    timings.render = performance.now() - renderStarted;
    renderDiagnostics(filtered.rows.length);
  }

  function applyFilters() {
    if (!metadata || rows.length === 0) {
      return;
    }
    const sequence = renderSequence + 1;
    renderSequence = sequence;
    const filtered = filterRows();
    const maxPoints = metadata.render_guardrail ? metadata.render_guardrail.max_points : 25000;
    updateFilterSummary(filtered);
    timings.trace = null;
    timings.render = null;

    if (filtered.rows.length === 0) {
      pendingAxisRanges = null;
      purgeChart();
      showGuardrail("No non-zero net issuance points match the current controls.");
      renderSp500Status();
      renderDiagnostics(0);
      return;
    }

    if (filtered.rows.length > maxPoints) {
      pendingAxisRanges = null;
      purgeChart();
      showGuardrail(
        `Filtered result has ${window.MacroObservatory.formatInteger(filtered.rows.length)} chart points. Narrow controls to ${window.MacroObservatory.formatInteger(maxPoints)} points or fewer before rendering.`
      );
      renderSp500Status();
      renderDiagnostics(filtered.rows.length);
      return;
    }

    hideGuardrail();
    renderChart(filtered, sequence).catch((error) => {
      window.MacroObservatory.showError(error.message);
    });
  }

  function scheduleApplyFilters() {
    if (applyTimer !== null) {
      window.clearTimeout(applyTimer);
    }
    applyTimer = window.setTimeout(() => {
      applyTimer = null;
      applyFilters();
    }, FILTER_DEBOUNCE_MS);
  }

  function currentChartAxisRanges() {
    const chart = element("treasury-securities-chart");
    const fullLayout = chart._fullLayout || {};
    const ranges = {};
    if (fullLayout.xaxis && Array.isArray(fullLayout.xaxis.range)) {
      ranges.x = [String(fullLayout.xaxis.range[0]), String(fullLayout.xaxis.range[1])];
    }
    if (fullLayout.yaxis && Array.isArray(fullLayout.yaxis.range)) {
      const y0 = Number(fullLayout.yaxis.range[0]);
      const y1 = Number(fullLayout.yaxis.range[1]);
      if (Number.isFinite(y0) && Number.isFinite(y1) && y0 !== y1) {
        ranges.y = [y0, y1];
      }
    }
    if (
      controls().sp500Overlay.checked
      && fullLayout.yaxis2
      && Array.isArray(fullLayout.yaxis2.range)
    ) {
      const y20 = Number(fullLayout.yaxis2.range[0]);
      const y21 = Number(fullLayout.yaxis2.range[1]);
      if (Number.isFinite(y20) && Number.isFinite(y21) && y20 !== y21) {
        ranges.y2 = [y20, y21];
      }
    }
    return ranges;
  }

  function axisNumberForUrl(value) {
    return String(Number(Number(value).toPrecision(12)));
  }

  function buildShareUrl() {
    const ui = controls();
    const params = new URLSearchParams();
    const ranges = currentChartAxisRanges();
    params.set("v", SHARE_STATE_VERSION);
    params.set("freq", ui.frequency.value);
    params.set("types", selectedSecurityTypeList(ui).join(","));
    if (ui.cumulative.checked) {
      params.set("cum", "1");
    }
    if (ui.sp500Overlay.checked && sp500Available()) {
      params.set("sp500", "1");
    }
    if (Array.isArray(ranges.x)) {
      params.set("x0", ranges.x[0]);
      params.set("x1", ranges.x[1]);
    }
    if (Array.isArray(ranges.y)) {
      params.set("y0", axisNumberForUrl(ranges.y[0]));
      params.set("y1", axisNumberForUrl(ranges.y[1]));
    }
    if (ui.sp500Overlay.checked && Array.isArray(ranges.y2)) {
      params.set("sp500y0", axisNumberForUrl(ranges.y2[0]));
      params.set("sp500y1", axisNumberForUrl(ranges.y2[1]));
    }

    const url = new URL(window.location.href);
    url.hash = params.toString();
    return url.toString();
  }

  function setCopyFeedback(message, feedbackButton) {
    const ui = controls();
    const status = element("copy-link-status");
    if (copyFeedbackTimer !== null) {
      window.clearTimeout(copyFeedbackTimer);
    }
    copyFeedbackTargets.forEach((button) => {
      button.textContent = "Copy Link";
    });
    copyFeedbackTargets = [ui.copyLink];
    if (feedbackButton && feedbackButton !== ui.copyLink) {
      copyFeedbackTargets.push(feedbackButton);
    }
    copyFeedbackTargets.forEach((button) => {
      button.textContent = message === "Copied" ? "Copied" : "Link Ready";
    });
    status.textContent = message;
    copyFeedbackTimer = window.setTimeout(() => {
      copyFeedbackTargets.forEach((button) => {
        button.textContent = "Copy Link";
      });
      copyFeedbackTargets = [];
      status.textContent = "";
      copyFeedbackTimer = null;
    }, COPY_FEEDBACK_MS);
  }

  function fallbackCopy(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.setAttribute("readonly", "");
    textArea.style.position = "fixed";
    textArea.style.left = "-9999px";
    document.body.appendChild(textArea);
    textArea.select();
    let copied = false;
    try {
      copied = document.execCommand("copy");
    } catch (_error) {
      copied = false;
    }
    document.body.removeChild(textArea);
    return copied;
  }

  async function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch (_error) {
        return fallbackCopy(text);
      }
    }
    return fallbackCopy(text);
  }

  async function copyShareLink(feedbackButton) {
    const shareUrl = buildShareUrl();
    window.history.replaceState(null, "", shareUrl);
    const copied = await copyText(shareUrl);
    setCopyFeedback(copied ? "Copied" : "Link in address bar", feedbackButton);
  }

  function setupControls() {
    renderFrequencyOptions();
    renderSecurityTypeControls();
    resetControls();
    applySharedControlState(parseSharedState());
    const ui = controls();
    if (!sp500Available()) {
      ui.sp500Overlay.checked = false;
      ui.sp500Overlay.disabled = true;
    }
    renderSp500Status();
    ui.frequency.addEventListener("change", scheduleApplyFilters);
    ui.cumulative.addEventListener("change", scheduleApplyFilters);
    ui.securityTypeInputs.forEach((input) => {
      input.addEventListener("change", scheduleApplyFilters);
    });
    ui.sp500Overlay.addEventListener("change", scheduleApplyFilters);
    ui.reset.addEventListener("click", () => {
      pendingAxisRanges = null;
      resetControls();
      scheduleApplyFilters();
    });
    ui.copyLink.addEventListener("click", () => {
      copyShareLink().catch((error) => {
        window.MacroObservatory.showError(error.message);
      });
    });
  }

  function decodePayload(payload) {
    if (!payload || !Array.isArray(payload.columns) || !Array.isArray(payload.data)) {
      throw new Error("Treasury securities JSON artifact is not in split orientation.");
    }
    columnIndex = {};
    payload.columns.forEach((column, index) => {
      columnIndex[column] = index;
    });
    [
      "frequency",
      "date",
      "security_type",
      "issued",
      "maturing",
      "net_issuance"
    ].forEach(requiredColumn);
    rows = payload.data;
    const securityTypeIndex = requiredColumn("security_type");
    securityTypes = orderedSecurityTypes(
      new Set(rows.map((row) => String(row[securityTypeIndex] || "Unknown")))
    );
  }

  function decodeSp500Payload(payload) {
    if (!payload || !Array.isArray(payload.columns) || !Array.isArray(payload.data)) {
      throw new Error("SP500 JSON artifact is not in split orientation.");
    }
    sp500ColumnIndex = {};
    payload.columns.forEach((column, index) => {
      sp500ColumnIndex[column] = index;
    });
    ["date", "value"].forEach(requiredSp500Column);
    const dateIndex = requiredSp500Column("date");
    sp500Rows = payload.data
      .map((row) => ({
        date: String(row[dateIndex] || ""),
        value: numericSp500Value(row, "value")
      }))
      .filter((row) => row.date && row.value !== null)
      .sort((left, right) => left.date.localeCompare(right.date));
  }

  async function fetchSplitJson(url, timingTarget) {
    const fetchStarted = performance.now();
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Request failed for ${url}: ${response.status}`);
    }
    const text = await response.text();
    timingTarget.fetch = performance.now() - fetchStarted;
    const parseStarted = performance.now();
    const payload = JSON.parse(text);
    timingTarget.parse = performance.now() - parseStarted;
    return payload;
  }

  async function loadSp500Artifacts() {
    try {
      const [metadataPayload, dataPayload] = await Promise.all([
        window.MacroObservatory.fetchJson(SP500_METADATA_URL),
        fetchSplitJson(SP500_DATA_URL, sp500Timings)
      ]);
      sp500Metadata = metadataPayload;
      decodeSp500Payload(dataPayload);
    } catch (error) {
      sp500Error = error && error.message ? error.message : String(error);
      sp500Metadata = null;
      sp500Rows = [];
      sp500ColumnIndex = {};
    }
  }

  async function initialize() {
    window.MacroObservatory.enableChartExpansion({
      buttonId: "treasury-securities-chart-expand",
      frameId: "treasury-securities-chart-frame",
      chartId: "treasury-securities-chart",
      title: "Treasury Securities Net Issuance",
      metaId: "filtered-range-label",
      headerActions: [
        {
          id: "treasury-securities-expanded-copy-link",
          label: "Copy Link",
          ariaLabel: "Copy link to current Treasury Securities chart view",
          onClick: ({ button }) => copyShareLink(button)
        }
      ]
    });

    try {
      metadata = await window.MacroObservatory.fetchJson(METADATA_URL);
      renderMetadata();
      element("loading-row").textContent = "Loading Treasury securities and market context artifacts...";
      const sp500Promise = loadSp500Artifacts();
      const payload = await fetchSplitJson(DATA_URL, timings);
      await sp500Promise;
      decodePayload(payload);
      setupControls();
      window.MacroObservatory.hideLoading();
      applyFilters();
    } catch (error) {
      window.MacroObservatory.hideLoading();
      window.MacroObservatory.showError(error.message);
    }
  }

  document.addEventListener("DOMContentLoaded", initialize);
})();