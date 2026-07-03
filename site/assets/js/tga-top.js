(function () {
  "use strict";

  const DATA_URL = "../../data/tga-explorer.json";
  const METADATA_URL = "../../data/tga-explorer-metadata.json";
  const MILLIONS_TO_BILLIONS = 1000;
  const AGENCY_GROUPS = ["HHS", "USDA", "DoD", "SSA", "VA", "OPM", "TREAS", "DOT", "DHS", "DOL"];

  let metadata = null;
  let rows = [];
  let columnIndex = {};
  let availableDates = [];
  const timings = {
    fetch: null,
    parse: null,
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

  function formatMillions(value) {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return "n/a";
    }
    return value.toLocaleString("en-US", {
      maximumFractionDigits: 0
    });
  }


  function requiredColumn(name) {
    if (!(name in columnIndex)) {
      throw new Error(`TGA Top data is missing required column: ${name}`);
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

  function controls() {
    return {
      date: element("date-input"),
      previous: element("previous-date-button"),
      next: element("next-date-button"),
      latest: element("latest-date-button")
    };
  }

  function renderDiagnostics(selectedRows) {
    element("diagnostics-bar").textContent = [
      `Rows ${window.MacroObservatory.formatInteger(selectedRows)}`,
      `Data ${formatMs(timings.fetch)}`,
      `Parse ${formatMs(timings.parse)}`,
      `Render ${formatMs(timings.render)}`
    ].join(" | ");
  }

  function renderMetadata() {
    const dateRange = metadata.date_range || {};
    setText("dataset-summary", "Daily Treasury Statement snapshot of top deposits and withdrawals by selected date.");
    setText("built-at", window.MacroObservatory.formatIsoDateTime(metadata.dataset_built_at));
    setText("metric-latest-date", window.MacroObservatory.formatDate(dateRange.max));
  }

  function decodePayload(payload) {
    if (!payload || !Array.isArray(payload.columns) || !Array.isArray(payload.data)) {
      throw new Error("TGA Top JSON artifact is not in split orientation.");
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

  function buildAvailableDates() {
    const dates = new Set();
    rows.forEach((row) => {
      const value = rowValue(row, "record_date");
      if (value) {
        dates.add(String(value));
      }
    });
    availableDates = Array.from(dates).sort();
  }

  function selectedDateRows(dateValue) {
    if (!dateValue) {
      return [];
    }
    return rows.filter((row) => rowValue(row, "record_date") === dateValue);
  }

  function rowsForType(dateRows, transactionType) {
    return dateRows
      .filter((row) => rowValue(row, "transaction_type") === transactionType)
      .sort((left, right) => {
        const rightValue = numericRowValue(right, "transaction_today_amt") || 0;
        const leftValue = numericRowValue(left, "transaction_today_amt") || 0;
        if (rightValue !== leftValue) {
          return rightValue - leftValue;
        }
        return String(rowValue(left, "transaction_catg") || "").localeCompare(
          String(rowValue(right, "transaction_catg") || "")
        );
      });
  }

  function sumColumn(selectedRows, columnName) {
    return selectedRows.reduce((total, row) => total + (numericRowValue(row, columnName) || 0), 0);
  }

  function appendAmountCell(row, value) {
    const cell = document.createElement("td");
    cell.className = "number-cell";
    cell.textContent = formatMillions(value);
    row.appendChild(cell);
  }

  function renderTable(bodyId, emptyId, selectedRows) {
    const body = element(bodyId);
    const empty = element(emptyId);
    window.MacroObservatory.clearChildren(body);
    empty.hidden = selectedRows.length > 0;

    selectedRows.forEach((sourceRow) => {
      const row = document.createElement("tr");
      window.MacroObservatory.appendTextCell(
        row,
        String(rowValue(sourceRow, "transaction_catg") || "Uncategorized")
      );
      appendAmountCell(row, numericRowValue(sourceRow, "transaction_today_amt"));
      appendAmountCell(row, numericRowValue(sourceRow, "transaction_mtd_amt"));
      appendAmountCell(row, numericRowValue(sourceRow, "transaction_fytd_amt"));
      body.appendChild(row);
    });
  }

  function pieSourceRows(withdrawals) {
    return withdrawals.filter((row) => {
      const category = String(rowValue(row, "transaction_catg") || "");
      const fytd = numericRowValue(row, "transaction_fytd_amt");
      return (
        category !== "" &&
        category !== "null" &&
        !category.toLowerCase().includes("public debt cash redemp") &&
        fytd !== null &&
        fytd > 0
      );
    });
  }

  function groupAgency(category) {
    const match = AGENCY_GROUPS.find((agency) => category.includes(agency));
    return match || category;
  }

  function rawPieData(withdrawals) {
    return pieSourceRows(withdrawals)
      .map((row) => ({
        label: String(rowValue(row, "transaction_catg") || "Uncategorized"),
        value: (numericRowValue(row, "transaction_fytd_amt") || 0) / MILLIONS_TO_BILLIONS
      }))
      .sort((left, right) => right.value - left.value || left.label.localeCompare(right.label));
  }

  function agencyPieData(withdrawals) {
    const grouped = new Map();
    pieSourceRows(withdrawals).forEach((row) => {
      const label = groupAgency(String(rowValue(row, "transaction_catg") || "Uncategorized"));
      const value = (numericRowValue(row, "transaction_fytd_amt") || 0) / MILLIONS_TO_BILLIONS;
      grouped.set(label, (grouped.get(label) || 0) + value);
    });
    return Array.from(grouped.entries())
      .map(([label, value]) => ({ label, value }))
      .sort((left, right) => right.value - left.value || left.label.localeCompare(right.label));
  }

  function pieLayout() {
    return {
      autosize: true,
      margin: { t: 16, r: 18, b: 18, l: 18 },
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#ffffff",
      font: {
        family: "Inter, Segoe UI, sans-serif",
        color: "#172033"
      },
      showlegend: false
    };
  }

  function pieConfig() {
    return {
      displaylogo: false,
      responsive: true
    };
  }

  function showPieMessage(messageId, message) {
    const element = window.MacroObservatory.getElement(messageId);
    element.textContent = message;
    element.hidden = false;
  }

  function hidePieMessage(messageId) {
    window.MacroObservatory.getElement(messageId).hidden = true;
  }

  function purgeChart(chartId) {
    if (window.Plotly) {
      window.Plotly.purge(chartId);
    }
  }

  async function renderPie(chartId, messageId, data) {
    if (data.length === 0) {
      purgeChart(chartId);
      showPieMessage(messageId, "No withdrawal FYTD rows match the pie chart filters for this date.");
      return;
    }
    hidePieMessage(messageId);
    await window.Plotly.react(
      chartId,
      [
        {
          type: "pie",
          labels: data.map((item) => item.label),
          values: data.map((item) => item.value),
          sort: false,
          direction: "clockwise",
          hole: 0.28,
          textinfo: "percent+label+value",
          textposition: "inside",
          hovertemplate: "%{label}<br>%{value:,.0f}B<br>%{percent}<extra></extra>",
          marker: {
            line: {
              color: "rgba(255, 255, 255, 0.82)",
              width: 1
            }
          }
        }
      ],
      pieLayout(),
      pieConfig()
    );
  }

  function previousAvailableDate(dateValue) {
    for (let index = availableDates.length - 1; index >= 0; index -= 1) {
      if (availableDates[index] < dateValue) {
        return availableDates[index];
      }
    }
    return null;
  }

  function nextAvailableDate(dateValue) {
    for (let index = 0; index < availableDates.length; index += 1) {
      if (availableDates[index] > dateValue) {
        return availableDates[index];
      }
    }
    return null;
  }

  function updateDateButtons(dateValue) {
    const ui = controls();
    ui.previous.disabled = previousAvailableDate(dateValue) === null;
    ui.next.disabled = nextAvailableDate(dateValue) === null;
    ui.latest.disabled = dateValue === availableDates[availableDates.length - 1];
  }

  function renderDateHelp(dateValue, selectedRows) {
    const latest = availableDates[availableDates.length - 1];
    if (selectedRows.length === 0) {
      setText("date-help", `No rows are available for ${dateValue || "the selected date"}. Latest available date is ${latest}.`);
      setText("control-date-status", "No rows");
      return;
    }
    setText("date-help", `${window.MacroObservatory.formatInteger(selectedRows.length)} rows are available for ${dateValue}.`);
    setText("control-date-status", dateValue);
  }

  async function renderSelectedDate() {
    if (!window.Plotly) {
      throw new Error("Plotly did not load. Check the CDN connection and reload the page.");
    }

    const renderStarted = performance.now();
    const ui = controls();
    const dateValue = ui.date.value;
    const dateRows = selectedDateRows(dateValue);
    const deposits = rowsForType(dateRows, "Deposits");
    const withdrawals = rowsForType(dateRows, "Withdrawals");
    const depositToday = sumColumn(deposits, "transaction_today_amt");
    const withdrawalToday = sumColumn(withdrawals, "transaction_today_amt");

    renderDateHelp(dateValue, dateRows);
    setText("metric-selected-date", window.MacroObservatory.formatDate(dateValue));
    setText("metric-deposit-count", window.MacroObservatory.formatInteger(deposits.length));
    setText("metric-withdrawal-count", window.MacroObservatory.formatInteger(withdrawals.length));
    setText("deposits-range-label", `${window.MacroObservatory.formatInteger(deposits.length)} rows, ${formatMillions(depositToday)}M today`);
    setText("withdrawals-range-label", `${window.MacroObservatory.formatInteger(withdrawals.length)} rows, ${formatMillions(withdrawalToday)}M today`);
    setText("raw-pie-range-label", `${dateValue}, FYTD in B`);
    setText("agency-pie-range-label", `${dateValue}, FYTD in B`);

    renderTable("deposits-table-body", "deposits-empty", deposits);
    renderTable("withdrawals-table-body", "withdrawals-empty", withdrawals);
    await Promise.all([
      renderPie("raw-pie-chart", "raw-pie-message", rawPieData(withdrawals)),
      renderPie("agency-pie-chart", "agency-pie-message", agencyPieData(withdrawals))
    ]);

    timings.render = performance.now() - renderStarted;
    renderDiagnostics(dateRows.length);
    updateDateButtons(dateValue);
  }

  function setupControls() {
    const ui = controls();
    const firstDate = availableDates[0];
    const latestDate = availableDates[availableDates.length - 1];
    ui.date.min = firstDate;
    ui.date.max = latestDate;
    ui.date.value = latestDate;

    ui.date.addEventListener("change", () => {
      renderSelectedDate().catch((error) => {
        window.MacroObservatory.showError(error.message);
      });
    });
    ui.previous.addEventListener("click", () => {
      const previous = previousAvailableDate(ui.date.value);
      if (previous !== null) {
        ui.date.value = previous;
        renderSelectedDate().catch((error) => {
          window.MacroObservatory.showError(error.message);
        });
      }
    });
    ui.next.addEventListener("click", () => {
      const next = nextAvailableDate(ui.date.value);
      if (next !== null) {
        ui.date.value = next;
        renderSelectedDate().catch((error) => {
          window.MacroObservatory.showError(error.message);
        });
      }
    });
    ui.latest.addEventListener("click", () => {
      ui.date.value = latestDate;
      renderSelectedDate().catch((error) => {
        window.MacroObservatory.showError(error.message);
      });
    });
  }

  async function initialize() {
    window.MacroObservatory.enableChartExpansion({
      buttonId: "raw-pie-expand",
      frameId: "raw-pie-frame",
      chartId: "raw-pie-chart",
      title: "Withdrawals FYTD By Category",
      metaId: "raw-pie-range-label"
    });
    window.MacroObservatory.enableChartExpansion({
      buttonId: "agency-pie-expand",
      frameId: "agency-pie-frame",
      chartId: "agency-pie-chart",
      title: "Withdrawals FYTD By Agency Group",
      metaId: "agency-pie-range-label"
    });

    try {
      metadata = await window.MacroObservatory.fetchJson(METADATA_URL);
      renderMetadata();
      element("loading-row").textContent = "Loading TGA Explorer data artifact...";
      const payload = await fetchSplitJson(DATA_URL);
      decodePayload(payload);
      buildAvailableDates();
      if (availableDates.length === 0) {
        throw new Error("TGA Top data has no available record dates.");
      }
      setupControls();
      window.MacroObservatory.hideLoading();
      await renderSelectedDate();
    } catch (error) {
      window.MacroObservatory.hideLoading();
      window.MacroObservatory.showError(error.message);
    }
  }

  document.addEventListener("DOMContentLoaded", initialize);
})();
