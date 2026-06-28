(function () {
  "use strict";

  const DATA_URL = "../../data/fed-net-liquidity.json";
  const USD_TRILLION = 1000000000000;
  const USD_BILLION = 1000000000;
  const METADATA_URL = "../../data/fed-net-liquidity-metadata.json";
  const SERIES_ORDER = ["fed_net_liquidity", "walcl", "rrp", "tga", "rem"];
  const SERIES_COLORS = {
    fed_net_liquidity: "#1f5fbf",
    walcl: "#172033",
    rrp: "#c33a2b",
    tga: "#16865a",
    rem: "#6d45a8"
  };

  const SERIES_WIDTHS = {
    fed_net_liquidity: 3.2,
    walcl: 1.8,
    rrp: 1.8,
    tga: 1.8,
    rem: 1.4
  };

  function toTrillions(value) {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return null;
    }
    return value / 1000000000000;
  }

  function seriesLabel(metadata, key) {
    return metadata.series && metadata.series[key] ? metadata.series[key].label : key;
  }

  function makeTrace(records, metadata, key) {
    const label = seriesLabel(metadata, key);
    return {
      x: records.map((row) => row.date),
      y: records.map((row) => toTrillions(row[key])),
      name: label,
      mode: "lines",
      type: "scatter",
      connectgaps: false,
      line: {
        color: SERIES_COLORS[key],
        width: SERIES_WIDTHS[key]
      },
      hovertemplate: `${label}<br>%{x}<br>%{y:.2f}T<extra></extra>`
    };
  }

  function renderChart(records, metadata) {
    if (!window.Plotly) {
      throw new Error("Plotly did not load. Check the CDN connection and reload the page.");
    }

    const traces = SERIES_ORDER.map((key) => makeTrace(records, metadata, key));
    const layout = {
      autosize: true,
      margin: { t: 20, r: 22, b: 56, l: 68 },
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#ffffff",
      font: {
        family: "Inter, Segoe UI, sans-serif",
        color: "#172033"
      },
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
        rangeslider: { visible: false },
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
        title: "Trillions of U.S. dollars",
        showgrid: true,
        gridcolor: "#e7ebf1",
        zerolinecolor: "#aab4c2"
      },
      hovermode: "x unified"
    };

    const config = {
      displaylogo: false,
      responsive: true
    };

    window.Plotly.newPlot("liquidity-chart", traces, layout, config);
  }

  function renderMetrics(records, metadata) {
    const latest = window.MacroObservatory.latestWithValue(records, "fed_net_liquidity");
    const dateRange = metadata.date_range || {};

    window.MacroObservatory.setText("formula-text", metadata.formula || "Formula unavailable");
    window.MacroObservatory.setText(
      "built-at",
      window.MacroObservatory.formatIsoDateTime(metadata.dataset_built_at)
    );
    window.MacroObservatory.setText("metric-row-count", window.MacroObservatory.formatInteger(metadata.row_count));
    window.MacroObservatory.setText(
      "date-range-label",
      `${window.MacroObservatory.formatDate(dateRange.min)} to ${window.MacroObservatory.formatDate(dateRange.max)}`
    );

    if (!latest) {
      window.MacroObservatory.setText("metric-latest-date", "n/a");
      window.MacroObservatory.setText("metric-latest-value", "n/a");
      window.MacroObservatory.setText("metric-latest-change", "n/a");
      return;
    }

    window.MacroObservatory.setText("metric-latest-date", latest.date);
    window.MacroObservatory.setText(
      "metric-latest-value",
      window.MacroObservatory.formatUsdCompact(latest.fed_net_liquidity)
    );
    window.MacroObservatory.setText(
      "metric-latest-change",
      window.MacroObservatory.formatUsdDelta(latest.fed_net_liquidity_diff)
    );
    window.MacroObservatory.getElement("metric-latest-change").className =
      window.MacroObservatory.valueToneClass(latest.fed_net_liquidity_diff);
  }

  function renderDetails(metadata) {
    window.MacroObservatory.setText("metadata-units", metadata.display_units || "n/a");
    window.MacroObservatory.setText("metadata-sources", (metadata.source_dataset_ids || []).join(", "));
    window.MacroObservatory.setText("metadata-policy", metadata.forward_fill_policy || "n/a");

    const sourceRows = metadata.source_rows || {};
    const list = window.MacroObservatory.getElement("source-row-list");
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

  function tableUsdTrillions(value) {
    return window.MacroObservatory.formatUsdFixedUnit(value, USD_TRILLION, "T", 2);
  }

  function tableUsdBillions(value) {
    return window.MacroObservatory.formatUsdFixedUnit(value, USD_BILLION, "B", 1);
  }

  function tableUsdBillionsDelta(value) {
    return window.MacroObservatory.formatUsdDeltaFixedUnit(value, USD_BILLION, "B", 1);
  }

  function renderRecentTable(records) {
    const tbody = window.MacroObservatory.getElement("recent-table-body");
    window.MacroObservatory.clearChildren(tbody);

    records
      .filter((row) => row.fed_net_liquidity !== null && row.fed_net_liquidity !== undefined)
      .slice(-12)
      .reverse()
      .forEach((row) => {
        const tableRow = document.createElement("tr");
        window.MacroObservatory.appendTextCell(tableRow, row.date, "");
        window.MacroObservatory.appendTextCell(
          tableRow,
          tableUsdTrillions(row.fed_net_liquidity),
          "number-cell"
        );
        window.MacroObservatory.appendTextCell(
          tableRow,
          tableUsdBillionsDelta(row.fed_net_liquidity_diff),
          `number-cell ${window.MacroObservatory.valueToneClass(row.fed_net_liquidity_diff)}`
        );
        window.MacroObservatory.appendTextCell(
          tableRow,
          tableUsdTrillions(row.walcl),
          "number-cell"
        );
        window.MacroObservatory.appendTextCell(
          tableRow,
          tableUsdBillions(row.rrp),
          "number-cell"
        );
        window.MacroObservatory.appendTextCell(
          tableRow,
          tableUsdBillions(row.tga),
          "number-cell"
        );
        window.MacroObservatory.appendTextCell(
          tableRow,
          tableUsdBillions(row.rem),
          "number-cell"
        );
        tbody.appendChild(tableRow);
      });
  }

  function initialize() {
    window.MacroObservatory.enableChartExpansion({
      buttonId: "liquidity-chart-expand",
      frameId: "liquidity-chart-frame",
      chartId: "liquidity-chart",
      title: "Fed Net Liquidity",
      metaId: "date-range-label"
    });

    Promise.all([
      window.MacroObservatory.fetchJson(DATA_URL),
      window.MacroObservatory.fetchJson(METADATA_URL)
    ])
      .then(([records, metadata]) => {
        renderMetrics(records, metadata);
        renderDetails(metadata);
        renderRecentTable(records);
        renderChart(records, metadata);
        window.MacroObservatory.hideLoading();
      })
      .catch((error) => {
        window.MacroObservatory.hideLoading();
        window.MacroObservatory.showError(error.message);
      });
  }

  document.addEventListener("DOMContentLoaded", initialize);
})();
