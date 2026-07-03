(function () {
  "use strict";

  const DATA_URL = "../../data/treasurydirect-issued-maturing.json";
  const METADATA_URL = "../../data/treasurydirect-issued-maturing-metadata.json";
  const USD_BILLION = 1000000000;
  const COLUMNS = [
    "date",
    "issued_bills",
    "maturing_bills",
    "bills_change",
    "projected_change_bills",
    "issued_notes",
    "maturing_notes",
    "notes_change",
    "projected_change_notes",
    "issued_bonds",
    "maturing_bonds",
    "bonds_change",
    "projected_change_bonds",
    "issued",
    "maturing",
    "change",
    "change_with_weekend",
    "weekend",
    "projected_change",
    "auction",
    "auction_issuing",
    "offering_amount",
    "soma_tendered"
  ];
  const SIGNED_COLUMNS = new Set([
    "bills_change",
    "projected_change_bills",
    "notes_change",
    "projected_change_notes",
    "bonds_change",
    "projected_change_bonds",
    "change",
    "change_with_weekend",
    "weekend",
    "projected_change"
  ]);
  const AMOUNT_COLUMNS = new Set(COLUMNS.filter((column) => !["date", "auction", "auction_issuing"].includes(column)));
  const GROUP_START_COLUMNS = new Set([
    "issued_bills",
    "issued_notes",
    "issued_bonds",
    "issued",
    "auction"
  ]);
  const COLLAPSIBLE_GROUPS = {
    bills: {
      label: "Bills",
      collapsedClass: "group-collapsed-bills",
      headerSelector: '[data-group-header="bills"]',
      toggleSelector: '[data-group-toggle="bills"]'
    },
    notes: {
      label: "Notes",
      collapsedClass: "group-collapsed-notes",
      headerSelector: '[data-group-header="notes"]',
      toggleSelector: '[data-group-toggle="notes"]'
    },
    bonds: {
      label: "Bonds",
      collapsedClass: "group-collapsed-bonds",
      headerSelector: '[data-group-header="bonds"]',
      toggleSelector: '[data-group-toggle="bonds"]'
    }
  };
  const COLLAPSIBLE_COLUMNS = {
    issued_bills: { group: "bills", role: "issued", summary: false },
    maturing_bills: { group: "bills", role: "maturing", summary: false },
    bills_change: { group: "bills", role: "change", summary: true },
    projected_change_bills: { group: "bills", role: "projected", summary: false },
    issued_notes: { group: "notes", role: "issued", summary: false },
    maturing_notes: { group: "notes", role: "maturing", summary: false },
    notes_change: { group: "notes", role: "change", summary: true },
    projected_change_notes: { group: "notes", role: "projected", summary: false },
    issued_bonds: { group: "bonds", role: "issued", summary: false },
    maturing_bonds: { group: "bonds", role: "maturing", summary: false },
    bonds_change: { group: "bonds", role: "change", summary: true },
    projected_change_bonds: { group: "bonds", role: "projected", summary: false }
  };

  let metadata = null;
  let rows = [];
  let columnIndex = {};
  const collapsedGroups = new Set();
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

  function requiredColumn(name) {
    if (!(name in columnIndex)) {
      throw new Error(`TreasuryDirect issued/maturing data is missing required column: ${name}`);
    }
    return columnIndex[name];
  }

  function rowValue(row, columnName) {
    return row[requiredColumn(columnName)];
  }

  function numericRowValue(row, columnName) {
    const rawValue = rowValue(row, columnName);
    if (rawValue === null || rawValue === undefined || rawValue === "") {
      return null;
    }
    const value = Number(rawValue);
    return Number.isFinite(value) ? value : null;
  }

  function formatBillions(value, signed) {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return "n/a";
    }
    const abs = Math.abs(value);
    const formatted = (abs / USD_BILLION).toLocaleString("en-US", {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1
    });
    if (!signed || value === 0) {
      return `${value < 0 ? "-" : ""}$${formatted}B`;
    }
    return `${value > 0 ? "+" : "-"}$${formatted}B`;
  }

  function valueToneClass(value, signed) {
    if (!signed) {
      return "neutral";
    }
    return window.MacroObservatory.valueToneClass(value);
  }

  function applyCellAttributes(cell, attributes) {
    Object.entries(attributes || {}).forEach(([name, value]) => {
      cell.setAttribute(name, value);
    });
  }

  function columnPresentation(columnName) {
    const classes = [];
    const attributes = {};
    const collapseMetadata = COLLAPSIBLE_COLUMNS[columnName];

    if (GROUP_START_COLUMNS.has(columnName)) {
      classes.push("group-start");
    }
    if (collapseMetadata) {
      classes.push("collapsible-column");
      classes.push(collapseMetadata.summary ? "group-summary" : "collapsible-extra");
      attributes["data-group"] = collapseMetadata.group;
      attributes["data-column-role"] = collapseMetadata.role;
    }

    return {
      className: classes.join(" "),
      attributes
    };
  }

  function appendAmountCell(row, sourceRow, columnName, className, attributes) {
    const value = numericRowValue(sourceRow, columnName);
    const signed = SIGNED_COLUMNS.has(columnName);
    const cell = document.createElement("td");
    cell.className = ["number-cell", valueToneClass(value, signed), className]
      .filter(Boolean)
      .join(" ");
    applyCellAttributes(cell, attributes);
    cell.textContent = formatBillions(value, signed);
    row.appendChild(cell);
  }

  function appendTextCell(row, value, className, attributes) {
    const cell = document.createElement("td");
    cell.textContent = value || "";
    if (className) {
      cell.className = className;
    }
    applyCellAttributes(cell, attributes);
    row.appendChild(cell);
  }

  function updateGroupVisibility() {
    const table = document.querySelector(".issued-maturing-table");
    Object.entries(COLLAPSIBLE_GROUPS).forEach(([groupId, group]) => {
      const collapsed = collapsedGroups.has(groupId);
      const header = document.querySelector(group.headerSelector);
      const toggle = document.querySelector(group.toggleSelector);

      if (table) {
        table.classList.toggle(group.collapsedClass, collapsed);
      }
      if (header) {
        header.colSpan = collapsed ? 1 : 4;
      }
      if (toggle) {
        toggle.setAttribute("aria-expanded", String(!collapsed));
        toggle.setAttribute("aria-label", `${collapsed ? "Expand" : "Collapse"} ${group.label} columns`);
        const symbol = toggle.querySelector(".group-toggle-symbol");
        if (symbol) {
          symbol.textContent = collapsed ? "+" : "-";
        }
      }
    });
  }

  function setupGroupToggles() {
    Object.entries(COLLAPSIBLE_GROUPS).forEach(([groupId, group]) => {
      const toggle = document.querySelector(group.toggleSelector);
      if (!toggle) {
        return;
      }
      toggle.addEventListener("click", () => {
        if (collapsedGroups.has(groupId)) {
          collapsedGroups.delete(groupId);
        } else {
          collapsedGroups.add(groupId);
        }
        updateGroupVisibility();
      });
    });
    updateGroupVisibility();
  }

  function renderDiagnostics() {
    element("diagnostics-bar").textContent = [
      `Rows ${window.MacroObservatory.formatInteger(rows.length)}`,
      `Data ${formatMs(timings.fetch)}`,
      `Parse ${formatMs(timings.parse)}`,
      `Render ${formatMs(timings.render)}`
    ].join(" | ");
  }

  function renderSourceRows() {
    const sourceRows = metadata.source_rows || {};
    const container = element("source-row-list");
    window.MacroObservatory.clearChildren(container);

    Object.entries(sourceRows).forEach(([key, value]) => {
      const item = document.createElement("div");
      item.className = "source-row-item";

      const label = document.createElement("span");
      label.className = "source-row-key";
      label.textContent = key;

      const count = document.createElement("span");
      count.className = "source-row-value";
      count.textContent = window.MacroObservatory.formatInteger(value);

      item.appendChild(label);
      item.appendChild(count);
      container.appendChild(item);
    });
  }

  function renderMetadata() {
    const dateRange = metadata.date_range || {};
    const startDate = metadata.query_window_start_date || dateRange.min;
    const endDate = metadata.query_window_end_date_exclusive || dateRange.max;
    setText(
      "dataset-summary",
      "Current TreasuryDirect issued, maturing, projected, and auction-window report generated from the rolling TA_WS securities window."
    );
    setText("built-at", window.MacroObservatory.formatIsoDateTime(metadata.dataset_built_at));
    setText("metric-window-start", window.MacroObservatory.formatDate(startDate));
    setText("metric-window-end", window.MacroObservatory.formatDate(endDate));
    setText("metric-row-count", window.MacroObservatory.formatInteger(metadata.row_count));
    setText("metadata-units", `${metadata.source_units || "U.S. dollars"}; displayed in billions.`);
    setText("metadata-date-policy", metadata.date_policy || "Current-window source dates.");
    setText("metadata-weekend-policy", metadata.weekend_policy || "Weekend changes roll into the next weekday.");
    setText("metadata-projection-policy", metadata.projection_policy || "Projected values use issue-date source rows.");
    setText("report-range-label", `${window.MacroObservatory.formatDate(dateRange.min)} to ${window.MacroObservatory.formatDate(dateRange.max)}`);
    renderSourceRows();
  }

  function decodePayload(payload) {
    if (!payload || !Array.isArray(payload.columns) || !Array.isArray(payload.data)) {
      throw new Error("TreasuryDirect issued/maturing JSON artifact is not in split orientation.");
    }
    columnIndex = {};
    payload.columns.forEach((column, index) => {
      columnIndex[column] = index;
    });
    COLUMNS.forEach(requiredColumn);
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

  function renderMetricLatestChange() {
    const latestRow = rows.length > 0 ? rows[rows.length - 1] : null;
    if (!latestRow) {
      setText("metric-latest-change", "n/a");
      return;
    }
    const adjusted = numericRowValue(latestRow, "change_with_weekend");
    const regular = numericRowValue(latestRow, "change");
    const value = adjusted === null ? regular : adjusted;
    setText("metric-latest-change", formatBillions(value, true));
    element("metric-latest-change").className = valueToneClass(value, true);
  }

  function renderTable() {
    const renderStarted = performance.now();
    const body = element("report-table-body");
    window.MacroObservatory.clearChildren(body);

    rows.forEach((sourceRow) => {
      const row = document.createElement("tr");
      appendTextCell(row, String(rowValue(sourceRow, "date") || ""), "sticky-column date-cell");
      COLUMNS.slice(1).forEach((columnName) => {
        const columnMeta = columnPresentation(columnName);
        if (AMOUNT_COLUMNS.has(columnName)) {
          appendAmountCell(row, sourceRow, columnName, columnMeta.className, columnMeta.attributes);
          return;
        }
        appendTextCell(
          row,
          String(rowValue(sourceRow, columnName) || ""),
          [columnName === "auction" ? "auction-marker-cell" : "", columnMeta.className]
            .filter(Boolean)
            .join(" "),
          columnMeta.attributes
        );
      });
      body.appendChild(row);
    });

    timings.render = performance.now() - renderStarted;
    renderMetricLatestChange();
    renderDiagnostics();
  }

  async function initialize() {
    setupGroupToggles();
    try {
      metadata = await window.MacroObservatory.fetchJson(METADATA_URL);
      renderMetadata();
      element("loading-row").textContent = "Loading TreasuryDirect issued/maturing data artifact...";
      const payload = await fetchSplitJson(DATA_URL);
      decodePayload(payload);
      window.MacroObservatory.hideLoading();
      renderTable();
    } catch (error) {
      window.MacroObservatory.hideLoading();
      window.MacroObservatory.showError(error.message);
    }
  }

  document.addEventListener("DOMContentLoaded", initialize);
})();
