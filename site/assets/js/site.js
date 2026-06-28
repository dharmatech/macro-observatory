(function () {
  "use strict";

  const USD_TRILLION = 1000000000000;
  const USD_BILLION = 1000000000;

  function getElement(id) {
    const element = document.getElementById(id);
    if (!element) {
      throw new Error(`Missing element: ${id}`);
    }
    return element;
  }

  function setText(id, value) {
    getElement(id).textContent = value;
  }

  function clearChildren(element) {
    while (element.firstChild) {
      element.removeChild(element.firstChild);
    }
  }

  function fetchJson(url) {
    return fetch(url, { cache: "no-store" }).then((response) => {
      if (!response.ok) {
        throw new Error(`Request failed for ${url}: ${response.status}`);
      }
      return response.json();
    });
  }

  function formatInteger(value) {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return "n/a";
    }
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value);
  }

  function formatDate(value) {
    if (!value) {
      return "n/a";
    }
    return value;
  }

  function formatIsoDateTime(value) {
    if (!value) {
      return "n/a";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit"
    }).format(date);
  }

  function formatUsdCompact(value) {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return "n/a";
    }
    const abs = Math.abs(value);
    if (abs >= USD_TRILLION) {
      return `${value < 0 ? "-" : ""}$${(abs / USD_TRILLION).toFixed(2)}T`;
    }
    if (abs >= USD_BILLION) {
      return `${value < 0 ? "-" : ""}$${(abs / USD_BILLION).toFixed(1)}B`;
    }
    return `${value < 0 ? "-" : ""}$${formatInteger(abs)}`;
  }

  function formatUsdFixedUnit(value, divisor, suffix, fractionDigits) {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return "n/a";
    }
    const abs = Math.abs(value);
    const formatted = (abs / divisor).toLocaleString("en-US", {
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits
    });
    return `${value < 0 ? "-" : ""}$${formatted}${suffix}`;
  }

  function formatUsdDeltaFixedUnit(value, divisor, suffix, fractionDigits) {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return "n/a";
    }
    if (value === 0) {
      return formatUsdFixedUnit(value, divisor, suffix, fractionDigits);
    }
    const prefix = value > 0 ? "+" : "-";
    const formatted = formatUsdFixedUnit(Math.abs(value), divisor, suffix, fractionDigits);
    return `${prefix}${formatted}`;
  }

  function formatUsdDelta(value) {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return "n/a";
    }
    if (value === 0) {
      return "$0";
    }
    const prefix = value > 0 ? "+" : "-";
    return `${prefix}${formatUsdCompact(Math.abs(value))}`;
  }

  function valueToneClass(value) {
    if (value === null || value === undefined || Number.isNaN(value) || value === 0) {
      return "neutral";
    }
    return value > 0 ? "positive" : "negative";
  }

  function latestWithValue(records, key) {
    for (let index = records.length - 1; index >= 0; index -= 1) {
      const row = records[index];
      if (row[key] !== null && row[key] !== undefined && !Number.isNaN(row[key])) {
        return row;
      }
    }
    return null;
  }

  function showError(message) {
    const alert = getElement("page-alert");
    alert.textContent = message;
    alert.hidden = false;
  }

  function hideLoading() {
    const loading = document.getElementById("loading-row");
    if (loading) {
      loading.hidden = true;
    }
  }

  function appendTextCell(row, value, className) {
    const cell = document.createElement("td");
    cell.textContent = value;
    if (className) {
      cell.className = className;
    }
    row.appendChild(cell);
    return cell;
  }

  function resizePlotlyChart(chart) {
    if (window.Plotly && window.Plotly.Plots && typeof window.Plotly.Plots.resize === "function") {
      window.Plotly.Plots.resize(chart);
    }
  }

  function schedulePlotlyResize(chart) {
    window.requestAnimationFrame(() => {
      resizePlotlyChart(chart);
      window.setTimeout(() => resizePlotlyChart(chart), 80);
    });
  }

  function enableChartExpansion(options) {
    const button = getElement(options.buttonId);
    const frame = getElement(options.frameId);
    const chart = getElement(options.chartId);
    const title = options.title || "Chart";
    let expanded = false;
    let scrollY = 0;

    const header = document.createElement("div");
    header.className = "chart-expand-header";

    const titleBlock = document.createElement("div");
    titleBlock.className = "chart-expand-title-block";

    const titleElement = document.createElement("strong");
    titleElement.className = "chart-expand-title";
    titleElement.textContent = title;

    const metaElement = document.createElement("span");
    metaElement.className = "chart-expand-meta";

    const actionBlock = document.createElement("div");
    actionBlock.className = "chart-expand-actions";

    const headerActions = Array.isArray(options.headerActions) ? options.headerActions.filter(Boolean) : [];
    headerActions.forEach((action) => {
      const actionButton = document.createElement("button");
      actionButton.type = "button";
      actionButton.className = action.className
        ? `chart-expand-action ${action.className}`
        : "chart-expand-action";
      actionButton.textContent = action.label || "Action";
      if (action.id) {
        actionButton.id = action.id;
      }
      if (action.ariaLabel) {
        actionButton.setAttribute("aria-label", action.ariaLabel);
      }
      if (action.title) {
        actionButton.title = action.title;
      }
      actionButton.addEventListener("click", (event) => {
        if (typeof action.onClick !== "function") {
          return;
        }
        try {
          const result = action.onClick({
            button: actionButton,
            event,
            expand,
            restore,
            isExpanded: () => expanded
          });
          if (result && typeof result.catch === "function") {
            result.catch((error) => {
              showError(error && error.message ? error.message : String(error));
            });
          }
        } catch (error) {
          showError(error && error.message ? error.message : String(error));
        }
      });
      actionBlock.appendChild(actionButton);
    });

    const restoreButton = document.createElement("button");
    restoreButton.type = "button";
    restoreButton.className = "chart-expand-restore";
    restoreButton.textContent = "Restore";
    actionBlock.appendChild(restoreButton);

    titleBlock.appendChild(titleElement);
    titleBlock.appendChild(metaElement);
    header.appendChild(titleBlock);
    header.appendChild(actionBlock);
    frame.insertBefore(header, frame.firstChild);

    button.setAttribute("aria-controls", options.frameId);
    button.setAttribute("aria-expanded", "false");

    function currentMetaText() {
      if (!options.metaId) {
        return "";
      }
      const meta = document.getElementById(options.metaId);
      return meta ? meta.textContent : "";
    }

    function syncHeaderMeta() {
      metaElement.textContent = currentMetaText();
    }

    function expand() {
      if (expanded) {
        return;
      }
      expanded = true;
      scrollY = window.scrollY;
      syncHeaderMeta();
      document.body.classList.add("chart-expanded-active");
      frame.classList.add("is-chart-expanded");
      frame.setAttribute("role", "dialog");
      frame.setAttribute("aria-label", `${title} expanded chart`);
      button.textContent = "Restore";
      button.setAttribute("aria-expanded", "true");
      restoreButton.focus({ preventScroll: true });
      schedulePlotlyResize(chart);
    }

    function restore() {
      if (!expanded) {
        return;
      }
      expanded = false;
      frame.classList.remove("is-chart-expanded");
      frame.removeAttribute("role");
      frame.removeAttribute("aria-label");
      document.body.classList.remove("chart-expanded-active");
      button.textContent = "Expand";
      button.setAttribute("aria-expanded", "false");
      button.focus({ preventScroll: true });
      window.scrollTo(0, scrollY);
      schedulePlotlyResize(chart);
    }

    button.addEventListener("click", () => {
      if (expanded) {
        restore();
      } else {
        expand();
      }
    });
    restoreButton.addEventListener("click", restore);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && expanded) {
        event.preventDefault();
        restore();
      }
    });
    window.addEventListener("resize", () => {
      if (expanded) {
        syncHeaderMeta();
        schedulePlotlyResize(chart);
      }
    });
  }

  window.MacroObservatory = {
    clearChildren,
    enableChartExpansion,
    fetchJson,
    formatDate,
    formatInteger,
    formatIsoDateTime,
    formatUsdCompact,
    formatUsdDeltaFixedUnit,
    formatUsdFixedUnit,
    formatUsdDelta,
    getElement,
    hideLoading,
    latestWithValue,
    setText,
    showError,
    appendTextCell,
    valueToneClass
  };
})();
