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

  window.MacroObservatory = {
    clearChildren,
    fetchJson,
    formatDate,
    formatInteger,
    formatIsoDateTime,
    formatUsdCompact,
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
