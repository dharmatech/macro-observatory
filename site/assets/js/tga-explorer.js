(function () {
  "use strict";

  const DATA_URL = "../../data/tga-explorer.json";
  const METADATA_URL = "../../data/tga-explorer-metadata.json";
  const DEFAULTS = {
    metric: "transaction_fytd_amt",
    yearStart: 2022,
    minimums: {
      transaction_today_amt: 1000,
      transaction_mtd_amt: 10000,
      transaction_fytd_amt: 115000
    },
    deposits: true,
    withdrawals: true,
    publicDebt: false,
    categoryFilter: false
  };
  const LEGACY_MINIMUMS = {
    transaction_today_amt: 1000,
    transaction_mtd_amt: 10000,
    transaction_fytd_amt: 100000
  };
  const LEGEND_CATEGORY_LIMIT = 80;
  const FILTER_DEBOUNCE_MS = 120;

  let metadata = null;
  let rows = [];
  let columnIndex = {};
  let categories = [];
  let applyTimer = null;
  let renderSequence = 0;
  let minimumWasCustomized = false;
  let lastMetricMinimum = DEFAULTS.minimums[DEFAULTS.metric];
  const timings = {
    fetch: null,
    parse: null,
    filter: null,
    trace: null,
    render: null
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

  function formatAmountMillions(value) {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return "n/a";
    }
    return `${value < 0 ? "-" : ""}${Math.abs(value).toLocaleString("en-US", {
      maximumFractionDigits: 0
    })}M`;
  }

  function metricLabel(metric) {
    if (metadata && metadata.series && metadata.series[metric]) {
      return metadata.series[metric].label;
    }
    return metric;
  }

  function metricMinimum(metric) {
    return DEFAULTS.minimums[metric] || LEGACY_MINIMUMS[metric] || 0;
  }

  function requiredColumn(name) {
    if (!(name in columnIndex)) {
      throw new Error(`TGA Explorer data is missing required column: ${name}`);
    }
    return columnIndex[name];
  }

  function rowValue(row, columnName) {
    return row[requiredColumn(columnName)];
  }

  function numericRowValue(row, columnName) {
    const value = Number(rowValue(row, columnName));
    return Number.isFinite(value) ? value : null;
  }

  function signedMetricValue(row, metric) {
    const value = numericRowValue(row, metric);
    if (value === null) {
      return null;
    }
    return rowValue(row, "transaction_type") === "Withdrawals" ? -Math.abs(value) : value;
  }

  function renderMetadata() {
    const dateRange = metadata.date_range || {};
    setText("dataset-summary", metadata.title || "Treasury deposits and withdrawals dataset");
    setText("built-at", window.MacroObservatory.formatIsoDateTime(metadata.dataset_built_at));
    setText("metric-latest-date", window.MacroObservatory.formatDate(dateRange.max));
    setText("metric-row-count", window.MacroObservatory.formatInteger(metadata.row_count));
    setText("metric-filtered-row-count", "Loading");
    setText("metric-category-count", window.MacroObservatory.formatInteger(metadata.category_count));
    setText("metadata-units", metadata.display_units || "n/a");
    setText("metadata-source", metadata.source_endpoint || "n/a");
    setText("metadata-policy", metadata.sign_policy || "n/a");

    const sourceRows = metadata.source_rows || {};
    const list = element("source-row-list");
    window.MacroObservatory.clearChildren(list);
    Object.keys(sourceRows)
      .sort()
      .forEach((key) => {
        const row = document.createElement("div");
        row.className = "source-row-item";

        const name = document.createElement("span");
        name.className = "source-row-key";
        name.textContent = key;

        const value = document.createElement("span");
        value.className = "source-row-value";
        value.textContent = window.MacroObservatory.formatInteger(sourceRows[key]);

        row.appendChild(name);
        row.appendChild(value);
        list.appendChild(row);
      });
  }

  function renderMetricOptions() {
    const select = element("metric-select");
    window.MacroObservatory.clearChildren(select);
    const metricColumns = metadata.metric_columns || [
      "transaction_today_amt",
      "transaction_mtd_amt",
      "transaction_fytd_amt"
    ];
    metricColumns.forEach((metric) => {
      const option = document.createElement("option");
      option.value = metric;
      option.textContent = metricLabel(metric);
      select.appendChild(option);
    });
    select.value = DEFAULTS.metric;
  }

  function controls() {
    return {
      metric: element("metric-select"),
      yearStart: element("year-start-input"),
      minimumAmount: element("minimum-amount-input"),
      deposits: element("deposits-checkbox"),
      withdrawals: element("withdrawals-checkbox"),
      publicDebt: element("public-debt-checkbox"),
      categoryFilter: element("category-filter-checkbox"),
      categorySelect: element("category-select"),
      reset: element("reset-button")
    };
  }

  function resetControls() {
    const ui = controls();
    ui.metric.value = DEFAULTS.metric;
    ui.yearStart.value = String(DEFAULTS.yearStart);
    ui.minimumAmount.value = String(metricMinimum(DEFAULTS.metric));
    ui.deposits.checked = DEFAULTS.deposits;
    ui.withdrawals.checked = DEFAULTS.withdrawals;
    ui.publicDebt.checked = DEFAULTS.publicDebt;
    ui.categoryFilter.checked = DEFAULTS.categoryFilter;
    ui.categorySelect.disabled = true;
    Array.from(ui.categorySelect.options).forEach((option) => {
      option.selected = false;
    });
    minimumWasCustomized = false;
    lastMetricMinimum = metricMinimum(DEFAULTS.metric);
  }

  function populateCategories() {
    const categoryIndex = requiredColumn("transaction_catg");
    const categorySet = new Set();
    rows.forEach((row) => {
      const value = row[categoryIndex];
      if (value !== null && value !== undefined && value !== "") {
        categorySet.add(String(value));
      }
    });
    categories = Array.from(categorySet).sort((left, right) => left.localeCompare(right));

    const select = element("category-select");
    window.MacroObservatory.clearChildren(select);
    const fragment = document.createDocumentFragment();
    categories.forEach((category) => {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      fragment.appendChild(option);
    });
    select.appendChild(fragment);
    setText("category-help", `${window.MacroObservatory.formatInteger(categories.length)} categories available`);
  }

  function selectedCategorySet(ui) {
    if (!ui.categoryFilter.checked) {
      return null;
    }
    return new Set(Array.from(ui.categorySelect.selectedOptions).map((option) => option.value));
  }

  function startDateFromYear(value) {
    const parsed = Number.parseInt(value, 10);
    const year = Number.isFinite(parsed) ? parsed : DEFAULTS.yearStart;
    return `${String(year).padStart(4, "0")}-10-01`;
  }

  function filterRows() {
    const ui = controls();
    const started = performance.now();
    const metric = ui.metric.value;
    const startDate = startDateFromYear(ui.yearStart.value);
    const minimum = Math.max(0, Number(ui.minimumAmount.value) || 0);
    const includeDeposits = ui.deposits.checked;
    const includeWithdrawals = ui.withdrawals.checked;
    const includePublicDebt = ui.publicDebt.checked;
    const selectedCategories = selectedCategorySet(ui);
    const rowIndexes = [];
    const values = [];
    const categoryCounts = new Map();
    let latestDate = null;

    const dateIndex = requiredColumn("record_date");
    const typeIndex = requiredColumn("transaction_type");
    const categoryIndex = requiredColumn("transaction_catg");

    for (let index = 0; index < rows.length; index += 1) {
      const row = rows[index];
      const date = row[dateIndex];
      if (date < startDate) {
        continue;
      }

      const type = row[typeIndex];
      if (type === "Deposits" && !includeDeposits) {
        continue;
      }
      if (type === "Withdrawals" && !includeWithdrawals) {
        continue;
      }

      const category = String(row[categoryIndex] || "");
      if (!includePublicDebt && category.toLowerCase().includes("public debt")) {
        continue;
      }
      if (selectedCategories !== null && !selectedCategories.has(category)) {
        continue;
      }

      const signedValue = signedMetricValue(row, metric);
      if (signedValue === null || Math.abs(signedValue) <= minimum) {
        continue;
      }

      rowIndexes.push(index);
      values.push(signedValue);
      categoryCounts.set(category, (categoryCounts.get(category) || 0) + 1);
      if (latestDate === null || date > latestDate) {
        latestDate = date;
      }
    }

    timings.filter = performance.now() - started;
    return {
      metric,
      startDate,
      minimum,
      rowIndexes,
      values,
      categoryCounts,
      latestDate
    };
  }

  function renderDiagnostics(filteredRows) {
    element("diagnostics-bar").textContent = [
      `Rows ${window.MacroObservatory.formatInteger(filteredRows)}`,
      `Data ${formatMs(timings.fetch)}`,
      `Parse ${formatMs(timings.parse)}`,
      `Filter ${formatMs(timings.filter)}`,
      `Trace ${formatMs(timings.trace)}`,
      `Render ${formatMs(timings.render)}`
    ].join(" | ");
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
      window.Plotly.purge("tga-chart");
    }
  }

  function updateFilterSummary(filtered) {
    const filteredRows = filtered.rowIndexes.length;
    const filteredCategories = filtered.categoryCounts.size;
    const maxRows = metadata.render_guardrail ? metadata.render_guardrail.max_rows : 10000;
    const range = metadata.date_range || {};
    setText("metric-filtered-row-count", window.MacroObservatory.formatInteger(filteredRows));
    setText("metric-category-count", window.MacroObservatory.formatInteger(filteredCategories));
    setText("metric-latest-date", filtered.latestDate || window.MacroObservatory.formatDate(range.max));
    setText("control-row-count", `${window.MacroObservatory.formatInteger(filteredRows)} rows`);
    setText(
      "filtered-range-label",
      `${window.MacroObservatory.formatInteger(filteredRows)} rows, ${window.MacroObservatory.formatInteger(filteredCategories)} categories, max ${window.MacroObservatory.formatInteger(maxRows)}`
    );
  }

  function buildTraces(filtered) {
    const started = performance.now();
    const grouped = new Map();
    const dateIndex = requiredColumn("record_date");
    const typeIndex = requiredColumn("transaction_type");
    const categoryIndex = requiredColumn("transaction_catg");

    filtered.rowIndexes.forEach((rowIndex, valueIndex) => {
      const row = rows[rowIndex];
      const category = String(row[categoryIndex] || "Uncategorized");
      let group = grouped.get(category);
      if (!group) {
        group = { x: [], y: [], customdata: [], absTotal: 0 };
        grouped.set(category, group);
      }
      const value = filtered.values[valueIndex];
      group.x.push(row[dateIndex]);
      group.y.push(value);
      group.customdata.push(row[typeIndex]);
      group.absTotal += Math.abs(value);
    });

    const showLegend = grouped.size <= LEGEND_CATEGORY_LIMIT;
    const traces = Array.from(grouped.entries())
      .sort((left, right) => right[1].absTotal - left[1].absTotal || left[0].localeCompare(right[0]))
      .map(([category, group]) => ({
        x: group.x,
        y: group.y,
        customdata: group.customdata,
        name: category,
        type: "bar",
        showlegend: showLegend,
        hovertemplate: "%{fullData.name}<br>%{x}<br>%{customdata}: %{y:,.0f}M<extra></extra>",
        marker: {
          line: {
            color: "rgba(255, 255, 255, 0.45)",
            width: 0.4
          }
        }
      }));

    timings.trace = performance.now() - started;
    return { traces, showLegend };
  }

  function chartLayout(metric, categoryCount, showLegend) {
    return {
      autosize: true,
      barmode: "relative",
      bargap: 0.08,
      margin: { t: 22, r: 26, b: 58, l: 72 },
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#ffffff",
      font: {
        family: "Inter, Segoe UI, sans-serif",
        color: "#172033"
      },
      showlegend: showLegend,
      legend: {
        orientation: "h",
        y: -0.24,
        x: 0,
        font: { size: 10 }
      },
      xaxis: {
        title: "",
        showgrid: true,
        gridcolor: "#e7ebf1"
      },
      yaxis: {
        title: `${metricLabel(metric)} (${metadata.display_units || "millions"})`,
        showgrid: true,
        gridcolor: "#e7ebf1",
        zerolinecolor: "#aab4c2",
        tickformat: ",.0f"
      },
      hovermode: "closest",
      annotations: showLegend
        ? []
        : [
            {
              text: `Legend hidden for ${window.MacroObservatory.formatInteger(categoryCount)} categories`,
              xref: "paper",
              yref: "paper",
              x: 1,
              y: 1.08,
              showarrow: false,
              align: "right",
              font: { size: 12, color: "#637083" }
            }
          ]
    };
  }

  function chartConfig() {
    return {
      displaylogo: false,
      responsive: true
    };
  }

  async function renderChart(filtered, sequence) {
    if (!window.Plotly) {
      throw new Error("Plotly did not load. Check the CDN connection and reload the page.");
    }
    const { traces, showLegend } = buildTraces(filtered);
    if (sequence !== renderSequence) {
      return;
    }
    const renderStarted = performance.now();
    await window.Plotly.react(
      "tga-chart",
      traces,
      chartLayout(filtered.metric, filtered.categoryCounts.size, showLegend),
      chartConfig()
    );
    if (sequence !== renderSequence) {
      return;
    }
    timings.render = performance.now() - renderStarted;
    renderDiagnostics(filtered.rowIndexes.length);
  }

  function applyFilters() {
    if (!metadata || rows.length === 0) {
      return;
    }
    const sequence = renderSequence + 1;
    renderSequence = sequence;
    const filtered = filterRows();
    const maxRows = metadata.render_guardrail ? metadata.render_guardrail.max_rows : 10000;
    updateFilterSummary(filtered);
    timings.trace = null;
    timings.render = null;

    if (filtered.rowIndexes.length === 0) {
      purgeChart();
      showGuardrail("No rows match the current filters.");
      renderDiagnostics(0);
      return;
    }

    if (filtered.rowIndexes.length > maxRows) {
      purgeChart();
      showGuardrail(
        `Filtered result has ${window.MacroObservatory.formatInteger(filtered.rowIndexes.length)} rows. Narrow filters to ${window.MacroObservatory.formatInteger(maxRows)} rows or fewer before rendering.`
      );
      renderDiagnostics(filtered.rowIndexes.length);
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

  function setupControls() {
    renderMetricOptions();
    resetControls();
    const ui = controls();

    ui.metric.addEventListener("change", () => {
      const nextMinimum = metricMinimum(ui.metric.value);
      const currentMinimum = Number(ui.minimumAmount.value);
      if (!minimumWasCustomized || currentMinimum === lastMetricMinimum) {
        ui.minimumAmount.value = String(nextMinimum);
        minimumWasCustomized = false;
      }
      lastMetricMinimum = nextMinimum;
      scheduleApplyFilters();
    });

    ui.yearStart.addEventListener("input", scheduleApplyFilters);
    ui.minimumAmount.addEventListener("input", () => {
      minimumWasCustomized = true;
      scheduleApplyFilters();
    });
    ui.deposits.addEventListener("change", scheduleApplyFilters);
    ui.withdrawals.addEventListener("change", scheduleApplyFilters);
    ui.publicDebt.addEventListener("change", scheduleApplyFilters);
    ui.categoryFilter.addEventListener("change", () => {
      ui.categorySelect.disabled = !ui.categoryFilter.checked;
      scheduleApplyFilters();
    });
    ui.categorySelect.addEventListener("change", scheduleApplyFilters);
    ui.reset.addEventListener("click", () => {
      resetControls();
      scheduleApplyFilters();
    });
  }

  function decodePayload(payload) {
    if (!payload || !Array.isArray(payload.columns) || !Array.isArray(payload.data)) {
      throw new Error("TGA Explorer JSON artifact is not in split orientation.");
    }
    columnIndex = {};
    payload.columns.forEach((column, index) => {
      columnIndex[column] = index;
    });
    [
      "record_date",
      "transaction_catg",
      "transaction_type",
      "transaction_today_amt",
      "transaction_mtd_amt",
      "transaction_fytd_amt"
    ].forEach(requiredColumn);
    rows = payload.data;
  }

  async function fetchSplitJson(url) {
    const fetchStarted = performance.now();
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Request failed for ${url}: ${response.status}`);
    }
    const text = await response.text();
    timings.fetch = performance.now() - fetchStarted;
    const parseStarted = performance.now();
    const payload = JSON.parse(text);
    timings.parse = performance.now() - parseStarted;
    return payload;
  }

  async function initialize() {
    try {
      metadata = await window.MacroObservatory.fetchJson(METADATA_URL);
      renderMetadata();
      setupControls();
      element("loading-row").textContent = "Loading TGA Explorer data artifact...";
      const payload = await fetchSplitJson(DATA_URL);
      decodePayload(payload);
      populateCategories();
      window.MacroObservatory.hideLoading();
      applyFilters();
    } catch (error) {
      window.MacroObservatory.hideLoading();
      window.MacroObservatory.showError(error.message);
    }
  }

  document.addEventListener("DOMContentLoaded", initialize);
})();
