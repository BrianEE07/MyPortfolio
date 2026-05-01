(function () {
  const payloadElement = document.getElementById("app-payload");
  const payload = payloadElement ? JSON.parse(payloadElement.textContent || "{}") : {};
  const holdingsCanvas = document.getElementById("holdingsChart");
  const holdingsLegend = document.getElementById("holdingsChartLegend");
  const fearGreedCanvas = document.getElementById("fearGreedChart");
  const sp500TrendCanvas = document.getElementById("sp500TrendChart");

  function updateThemeToggleState(theme) {
    const toggleButton = document.getElementById("themeToggle");
    if (!toggleButton) return;
    const nextThemeLabel = theme === "dark" ? "light" : "dark";
    toggleButton.dataset.theme = theme;
    toggleButton.setAttribute("aria-label", "Switch to " + nextThemeLabel + " mode");
    toggleButton.setAttribute("title", "Switch to " + nextThemeLabel + " mode");
  }

  function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    updateThemeToggleState(theme);
    try {
      localStorage.setItem("portfolio-theme", theme);
    } catch (error) {
      // Ignore storage failures and keep the in-memory theme.
    }
  }

  const themeToggle = document.getElementById("themeToggle");
  const initialTheme = document.documentElement.getAttribute("data-theme") || "light";
  updateThemeToggleState(initialTheme);

  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
      setTheme(currentTheme === "dark" ? "light" : "dark");
    });
  }

  const tabButtons = Array.from(document.querySelectorAll("[data-tab-target]"));
  const tabPanels = Array.from(document.querySelectorAll("[data-tab-panel]"));
  const summaryCardLabelElements = Array.from(
    document.querySelectorAll(".summary-card-label-en[data-label-full]")
  );
  const tooltipTriggers = Array.from(
    document.querySelectorAll("[data-tooltip-zh][data-tooltip-en]")
  );
  const categoryFiltersContainer = document.querySelector(".holdings-category-filters");
  const categoryFilterButtons = Array.from(
    document.querySelectorAll(".holdings-category-filter[data-category-filter], .holdings-category-track-segment[data-category-filter]")
  );
  let holdingsChartInstance = null;
  let fearGreedChartInstance = null;
  let sp500TrendChartInstance = null;
  let chartRelayoutTimeoutId = null;
  let chartRelayoutNeedsRebuild = false;
  let activeCategoryFilter = "all";
  let activeTabId = "overview";

  function shouldUseCompactSummaryLabels() {
    return window.matchMedia("(max-width: 640px) and (orientation: portrait)").matches
      || window.matchMedia("(max-width: 1024px) and (orientation: landscape)").matches
      || window.matchMedia("(max-width: 1024px)").matches;
  }

  function updateSummaryCardLabels() {
    const useCompactLabels = shouldUseCompactSummaryLabels();

    summaryCardLabelElements.forEach(function (element) {
      const fullLabel = element.dataset.labelFull || "";
      const compactLabel = element.dataset.labelCompact || fullLabel;
      element.textContent = useCompactLabels ? compactLabel : fullLabel;
    });
  }

  function hasChartData(chartPayload) {
    return Boolean(
      window.Chart
      && chartPayload
      && chartPayload.labels
      && chartPayload.labels.length
    );
  }

  function getChartPayload(chartName) {
    if (chartName === "holdings") return payload.holdingsChart;
    if (chartName === "fearGreed") return payload.fearGreedChart;
    if (chartName === "sp500Trend") return payload.sp500TrendChart;
    return null;
  }

  function isCanvasRenderable(canvas) {
    return Boolean(
      canvas
      && canvas.isConnected
      && canvas.getClientRects().length
      && canvas.parentElement
      && canvas.parentElement.clientWidth > 0
      && canvas.parentElement.clientHeight > 0
    );
  }

  function destroyChart(chart) {
    if (!chart) return null;
    chart.destroy();
    return null;
  }

  function clearHoldingsLegend() {
    if (!holdingsLegend) return;
    holdingsLegend.replaceChildren();
  }

  function renderHoldingsLegend(chartPayload) {
    if (!holdingsLegend) return;
    if (!chartPayload || !chartPayload.labels || !chartPayload.labels.length) {
      clearHoldingsLegend();
      return;
    }

    const fragment = document.createDocumentFragment();
    chartPayload.labels.forEach(function (label, index) {
      const legendItem = document.createElement("span");
      legendItem.className = "holdings-chart-legend-item";

      const swatch = document.createElement("span");
      swatch.className = "holdings-chart-legend-swatch";
      swatch.style.setProperty(
        "--legend-color",
        (chartPayload.colors || [])[index] || "#b86a17"
      );
      legendItem.appendChild(swatch);

      const text = document.createElement("span");
      text.textContent = label;
      const companyName = (chartPayload.companyNames || [])[index] || "";
      if (companyName && companyName !== label) {
        legendItem.title = label + " · " + companyName;
      }
      legendItem.appendChild(text);
      fragment.appendChild(legendItem);
    });

    holdingsLegend.replaceChildren(fragment);
  }

  function createHoldingsChart() {
    if (!hasChartData(payload.holdingsChart) || !isCanvasRenderable(holdingsCanvas)) {
      clearHoldingsLegend();
      return null;
    }

    const totalValue = (payload.holdingsChart.data || []).reduce(function (sum, item) {
      return sum + Number(item || 0);
    }, 0);
    renderHoldingsLegend(payload.holdingsChart);

    return new Chart(holdingsCanvas, {
      type: "doughnut",
      data: {
        labels: payload.holdingsChart.labels,
        datasets: [
          {
            data: payload.holdingsChart.data,
            backgroundColor: payload.holdingsChart.colors || ["#b86a17", "#d08a3e", "#e6b780"],
            borderWidth: 0,
            radius: "88%"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            boxPadding: 3,
            callbacks: {
              title: function (context) {
                const firstItem = context && context[0];
                if (!firstItem) return "";

                const dataIndex = firstItem.dataIndex;
                const symbol = (payload.holdingsChart.labels || [])[dataIndex] || "";
                const companyName = (payload.holdingsChart.companyNames || [])[dataIndex] || "";

                if (companyName && companyName !== symbol) {
                  return symbol + " · " + companyName;
                }

                return companyName || symbol;
              },
              label: function (context) {
                const numericValue = Number(context.raw || 0);
                const share = totalValue > 0 ? (numericValue / totalValue) * 100 : 0;
                return "$" + numericValue.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2
                }) + " (" + share.toFixed(1) + "%)";
              }
            }
          }
        }
      }
    });
  }

  function createFearGreedChart() {
    if (!hasChartData(payload.fearGreedChart) || !isCanvasRenderable(fearGreedCanvas)) {
      return null;
    }

    const xTickLimit = window.innerWidth < 700 ? 5 : 7;

    return new Chart(fearGreedCanvas, {
      type: "line",
      data: {
        labels: payload.fearGreedChart.labels,
        datasets: [
          {
            label: "Fear & Greed",
            data: payload.fearGreedChart.data,
            borderColor: "#b86a17",
            backgroundColor: "rgba(184, 106, 23, 0.16)",
            fill: true,
            tension: 0.25,
            pointRadius: 0,
            pointHoverRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false
        },
        scales: {
          x: {
            ticks: {
              autoSkip: true,
              maxTicksLimit: xTickLimit,
              maxRotation: 0,
              minRotation: 0
            }
          },
          y: {
            min: 0,
            max: 100
          }
        },
        plugins: {
          legend: {
            display: false
          }
        }
      }
    });
  }

  function createSp500TrendChart() {
    if (!hasChartData(payload.sp500TrendChart) || !isCanvasRenderable(sp500TrendCanvas)) {
      return null;
    }

    return new Chart(sp500TrendCanvas, {
      type: "line",
      data: {
        labels: payload.sp500TrendChart.labels,
        datasets: [
          {
            data: payload.sp500TrendChart.data,
            borderColor: "#34d399",
            backgroundColor: "rgba(52, 211, 153, 0.14)",
            fill: true,
            tension: 0.22,
            pointRadius: 0,
            pointHoverRadius: 3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false
        },
        scales: {
          x: {
            grid: {
              display: false
            },
            ticks: {
              maxTicksLimit: 6
            }
          },
          y: {
            ticks: {
              callback: function (value) {
                return Number(value).toLocaleString();
              }
            }
          }
        },
        plugins: {
          legend: {
            display: false
          }
        }
      }
    });
  }

  function refreshChart(chart, canvas, createChart, chartName) {
    if (!hasChartData(getChartPayload(chartName))) {
      if (chartName === "holdings") {
        clearHoldingsLegend();
      }
      return null;
    }
    if (!isCanvasRenderable(canvas)) {
      return chart;
    }

    if (!chart || chartRelayoutNeedsRebuild) {
      return createChart();
    }

    chart.resize();
    chart.update("resize");
    if (!chart.chartArea || chart.chartArea.width <= 0 || chart.chartArea.height <= 0) {
      chart.destroy();
      return createChart();
    }
    return chart;
  }

  function rebuildOrRefreshCharts() {
    if (chartRelayoutNeedsRebuild) {
      holdingsChartInstance = destroyChart(holdingsChartInstance);
      fearGreedChartInstance = destroyChart(fearGreedChartInstance);
      sp500TrendChartInstance = destroyChart(sp500TrendChartInstance);
    }

    holdingsChartInstance = refreshChart(
      holdingsChartInstance,
      holdingsCanvas,
      createHoldingsChart,
      "holdings"
    );
    fearGreedChartInstance = refreshChart(
      fearGreedChartInstance,
      fearGreedCanvas,
      createFearGreedChart,
      "fearGreed"
    );
    sp500TrendChartInstance = refreshChart(
      sp500TrendChartInstance,
      sp500TrendCanvas,
      createSp500TrendChart,
      "sp500Trend"
    );
    chartRelayoutNeedsRebuild = false;
  }

  function scheduleChartRelayout(forceRebuild) {
    chartRelayoutNeedsRebuild = chartRelayoutNeedsRebuild || Boolean(forceRebuild);
    if (chartRelayoutTimeoutId) {
      window.clearTimeout(chartRelayoutTimeoutId);
    }
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () {
        rebuildOrRefreshCharts();
      });
    });
    chartRelayoutTimeoutId = window.setTimeout(rebuildOrRefreshCharts, 160);
  }

  function activateTab(tabId) {
    if (activeTabId === "details" && tabId !== "details") {
      applyCategoryFilter("all", true, true, "auto");
    }

    clearActiveInfoChip();
    clearActiveSymbolLinkGroup();
    tabButtons.forEach(function (button) {
      const isActive = button.getAttribute("data-tab-target") === tabId;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-selected", isActive ? "true" : "false");
    });
    tabPanels.forEach(function (panel) {
      panel.classList.toggle("is-active", panel.getAttribute("data-tab-panel") === tabId);
    });
    activeTabId = tabId;
    scheduleChartRelayout(true);
  }

  tabButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      activateTab(button.getAttribute("data-tab-target"));
    });
  });

  const detailTable = document.querySelector(".holdings-detail-table");
  const detailTableBody = detailTable ? detailTable.querySelector("tbody") : null;
  const sortButtons = detailTable
    ? Array.from(detailTable.querySelectorAll(".sort-button[data-sort-key]"))
    : [];
  const symbolLinkGroups = Array.from(document.querySelectorAll("[data-symbol-link-group]"));
  const defaultSortKey = detailTableBody
    ? (detailTableBody.dataset.sortDefaultKey || "market-value")
    : "market-value";
  const defaultSortDirection = detailTableBody
    ? (detailTableBody.dataset.sortDefaultDirection || "desc")
    : "desc";
  const tooltipElement = document.createElement("div");
  tooltipElement.className = "info-chip-tooltip";
  document.body.appendChild(tooltipElement);
  let activeInfoChip = null;
  let activeSymbolLinkGroup = null;

  function setTooltipTriggerExpanded(trigger, isExpanded) {
    if (!trigger || !trigger.classList.contains("info-chip")) return;
    trigger.setAttribute("aria-expanded", isExpanded ? "true" : "false");
  }

  function positionInfoTooltip(trigger) {
    const chipRect = trigger.getBoundingClientRect();
    const tooltipRect = tooltipElement.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const tooltipLeft = Math.min(
      Math.max(12, chipRect.left + chipRect.width - tooltipRect.width + 10),
      viewportWidth - tooltipRect.width - 12
    );
    const preferredTop = chipRect.top - tooltipRect.height - 10;
    const tooltipTop = preferredTop >= 12
      ? preferredTop
      : chipRect.bottom + 10;

    tooltipElement.style.left = tooltipLeft + "px";
    tooltipElement.style.top = tooltipTop + "px";
  }

  function showInfoTooltip(trigger) {
    const tooltipText = [trigger.dataset.tooltipZh, trigger.dataset.tooltipEn]
      .filter(Boolean)
      .join("\n");
    if (!tooltipText) return;

    tooltipElement.textContent = tooltipText;
    tooltipElement.classList.add("is-visible");
    positionInfoTooltip(trigger);
  }

  function hideInfoTooltip() {
    tooltipElement.classList.remove("is-visible");
  }

  function clearActiveInfoChip() {
    setTooltipTriggerExpanded(activeInfoChip, false);
    activeInfoChip = null;
    hideInfoTooltip();
  }

  function setSymbolLinkExpanded(group, isExpanded) {
    if (!group) return;
    const toggleButton = group.querySelector("[data-symbol-link-toggle]");
    if (!toggleButton) return;
    toggleButton.setAttribute("aria-expanded", isExpanded ? "true" : "false");
    group.classList.toggle("is-link-revealed", isExpanded);
  }

  function clearActiveSymbolLinkGroup() {
    setSymbolLinkExpanded(activeSymbolLinkGroup, false);
    activeSymbolLinkGroup = null;
  }

  function setActiveSymbolLinkGroup(group) {
    if (activeSymbolLinkGroup && activeSymbolLinkGroup !== group) {
      setSymbolLinkExpanded(activeSymbolLinkGroup, false);
    }
    activeSymbolLinkGroup = group;
    setSymbolLinkExpanded(activeSymbolLinkGroup, true);
  }

  function toggleActiveSymbolLinkGroup(group) {
    if (activeSymbolLinkGroup === group) {
      clearActiveSymbolLinkGroup();
      return;
    }
    setActiveSymbolLinkGroup(group);
  }

  function setActiveInfoChip(chip) {
    if (activeInfoChip && activeInfoChip !== chip) {
      setTooltipTriggerExpanded(activeInfoChip, false);
    }
    activeInfoChip = chip;
    setTooltipTriggerExpanded(activeInfoChip, true);
    showInfoTooltip(activeInfoChip);
  }

  function toggleActiveInfoChip(chip) {
    if (activeInfoChip === chip) {
      clearActiveInfoChip();
      return;
    }
    setActiveInfoChip(chip);
  }

  activateTab("overview");
  updateSummaryCardLabels();

  function updateRankBadges(shouldHighlightTopHoldings) {
    if (!detailTableBody) return;
    const rows = Array.from(detailTableBody.querySelectorAll("tr"));
    let visibleIndex = 0;
    rows.forEach(function (row) {
      const rankElement = row.querySelector(".symbol-rank");
      if (!rankElement) return;
      rankElement.classList.remove("is-top-1", "is-top-2", "is-top-3");
      if (row.hidden) return;
      visibleIndex += 1;
      rankElement.textContent = String(visibleIndex);
      if (!shouldHighlightTopHoldings) return;
      if (visibleIndex === 1) rankElement.classList.add("is-top-1");
      if (visibleIndex === 2) rankElement.classList.add("is-top-2");
      if (visibleIndex === 3) rankElement.classList.add("is-top-3");
    });
  }

  function parseSortValue(row, key, type) {
    const rawValue = row.dataset["sort" + key.split("-").map(function (part) {
      return part.charAt(0).toUpperCase() + part.slice(1);
    }).join("")];

    if (type === "string") {
      return (rawValue || "").toLowerCase();
    }

    if (rawValue === undefined || rawValue === null || rawValue === "") {
      return null;
    }

    const numericValue = Number(rawValue);
    return Number.isFinite(numericValue) ? numericValue : null;
  }

  function compareRows(leftRow, rightRow, key, type, direction) {
    const leftValue = parseSortValue(leftRow, key, type);
    const rightValue = parseSortValue(rightRow, key, type);

    if (type === "string") {
      if (leftValue === rightValue) return 0;
      return direction === "asc"
        ? leftValue.localeCompare(rightValue)
        : rightValue.localeCompare(leftValue);
    }

    if (leftValue === null && rightValue === null) return 0;
    if (leftValue === null) return 1;
    if (rightValue === null) return -1;
    return direction === "asc" ? leftValue - rightValue : rightValue - leftValue;
  }

  function updateSortState(activeButton, direction) {
    sortButtons.forEach(function (button) {
      const isActive = button === activeButton;
      const headerCell = button.closest("th");
      button.classList.toggle("is-active", isActive);
      if (isActive) {
        button.dataset.sortDirection = direction;
      } else {
        delete button.dataset.sortDirection;
      }

      if (headerCell) {
        headerCell.setAttribute(
          "aria-sort",
          isActive
            ? (direction === "asc" ? "ascending" : "descending")
            : "none"
        );
      }
    });
  }

  function sortDetailsTable(sortKey, sortType, direction, activeButton) {
    if (!detailTableBody) return;
    const rows = Array.from(detailTableBody.querySelectorAll("tr"));
    rows.sort(function (leftRow, rightRow) {
      const result = compareRows(leftRow, rightRow, sortKey, sortType, direction);
      if (result !== 0) return result;
      return compareRows(leftRow, rightRow, "symbol", "string", "asc");
    });
    rows.forEach(function (row) {
      detailTableBody.appendChild(row);
    });
    updateSortState(activeButton, direction);
    applyCategoryFilter(activeCategoryFilter, false, false);
  }

  function updateCategoryFilterState(activeFilter) {
    categoryFilterButtons.forEach(function (button) {
      button.classList.toggle("is-active", button.dataset.categoryFilter === activeFilter);
    });
  }

  function scrollCategoryFilterChipIntoView(categoryId, behavior) {
    if (!categoryFiltersContainer) return;

    if (categoryId === "all") {
      categoryFiltersContainer.scrollTo({
        left: 0,
        behavior: behavior || "smooth"
      });
      return;
    }

    const activeChip = categoryFiltersContainer.querySelector(
      '.holdings-category-filter[data-category-filter="' + categoryId + '"]'
    );
    if (!activeChip) return;

    const containerRect = categoryFiltersContainer.getBoundingClientRect();
    const chipRect = activeChip.getBoundingClientRect();
    const chipIsFullyVisible = (
      chipRect.left >= containerRect.left
      && chipRect.right <= containerRect.right
    );
    if (chipIsFullyVisible) return;

    const targetScrollLeft = categoryFiltersContainer.scrollLeft
      + (chipRect.left - containerRect.left)
      - Math.max(8, (containerRect.width - chipRect.width) / 2);

    categoryFiltersContainer.scrollTo({
      left: Math.max(0, targetScrollLeft),
      behavior: behavior || "smooth"
    });
  }

  function applyCategoryFilter(categoryId, updateControls, shouldScrollIntoView, scrollBehavior) {
    if (!detailTableBody) return;
    activeCategoryFilter = categoryId || "all";
    const rows = Array.from(detailTableBody.querySelectorAll("tr"));
    rows.forEach(function (row) {
      const shouldShow = activeCategoryFilter === "all"
        || row.dataset.category === activeCategoryFilter;
      row.hidden = !shouldShow;
      row.classList.toggle("is-filtered-out", !shouldShow);
    });

    if (updateControls !== false) {
      updateCategoryFilterState(activeCategoryFilter);
    }

    if (shouldScrollIntoView !== false) {
      scrollCategoryFilterChipIntoView(activeCategoryFilter, scrollBehavior);
    }

    const activeSortButton = sortButtons.find(function (button) {
      return button.classList.contains("is-active");
    });
    const activeDirection = activeSortButton
      ? (activeSortButton.dataset.sortDirection || activeSortButton.dataset.defaultDirection || defaultSortDirection)
      : defaultSortDirection;
    const shouldHighlight = Boolean(
      activeSortButton
      && activeSortButton.dataset.sortKey === defaultSortKey
      && activeDirection === defaultSortDirection
    );
    updateRankBadges(shouldHighlight);
  }

  sortButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      const isActive = button.classList.contains("is-active");
      const initialDirection = button.dataset.defaultDirection
        || (button.dataset.sortType === "string" ? "asc" : "desc");
      const currentDirection = button.dataset.sortDirection || initialDirection;
      const defaultSortButton = detailTable
        ? detailTable.querySelector('.sort-button[data-sort-key="' + defaultSortKey + '"]')
        : null;

      if (!isActive) {
        sortDetailsTable(
          button.dataset.sortKey,
          button.dataset.sortType,
          initialDirection,
          button
        );
        return;
      }

      if (currentDirection === initialDirection) {
        sortDetailsTable(
          button.dataset.sortKey,
          button.dataset.sortType,
          currentDirection === "desc" ? "asc" : "desc",
          button
        );
        return;
      }

      if (button.dataset.sortKey === defaultSortKey || !defaultSortButton) {
        sortDetailsTable(
          button.dataset.sortKey,
          button.dataset.sortType,
          initialDirection,
          button
        );
        return;
      }

      sortDetailsTable(
        defaultSortKey,
        defaultSortButton.dataset.sortType,
        defaultSortDirection,
        defaultSortButton
      );
    });
  });

  const defaultSortButton = detailTable
    ? detailTable.querySelector('.sort-button[data-sort-key="' + defaultSortKey + '"]')
    : null;
  if (defaultSortButton) {
    sortDetailsTable(
      defaultSortButton.dataset.sortKey,
      defaultSortButton.dataset.sortType,
      defaultSortDirection,
      defaultSortButton
    );
  } else {
    updateRankBadges(false);
  }

  updateCategoryFilterState(activeCategoryFilter);

  tooltipTriggers.forEach(function (trigger) {
    setTooltipTriggerExpanded(trigger, false);
    trigger.addEventListener("click", function (event) {
      if (trigger.classList.contains("panel-source-link")) return;
      event.preventDefault();
      event.stopPropagation();
      toggleActiveInfoChip(trigger);
    });
    trigger.addEventListener("mousedown", function (event) {
      if (trigger.classList.contains("panel-source-link")) return;
      event.preventDefault();
      event.stopPropagation();
    });
    trigger.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        if (trigger.classList.contains("panel-source-link")) return;
        event.preventDefault();
        event.stopPropagation();
        toggleActiveInfoChip(trigger);
      }
    });
    trigger.addEventListener("mouseenter", function () {
      if (activeInfoChip && activeInfoChip !== trigger) return;
      showInfoTooltip(trigger);
    });
    trigger.addEventListener("mouseleave", function () {
      if (activeInfoChip === trigger) return;
      hideInfoTooltip();
    });
    trigger.addEventListener("focus", function () {
      if (activeInfoChip && activeInfoChip !== trigger) return;
      showInfoTooltip(trigger);
    });
    trigger.addEventListener("blur", function () {
      if (activeInfoChip === trigger) return;
      hideInfoTooltip();
    });
  });

  categoryFilterButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      applyCategoryFilter(button.dataset.categoryFilter || "all");
    });
  });

  symbolLinkGroups.forEach(function (group) {
    setSymbolLinkExpanded(group, false);
    const toggleButton = group.querySelector("[data-symbol-link-toggle]");
    if (!toggleButton) return;
    toggleButton.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      toggleActiveSymbolLinkGroup(group);
    });
  });

  document.addEventListener("click", function (event) {
    if (!activeInfoChip) return;
    if (event.target.closest(".info-chip") === activeInfoChip) return;
    clearActiveInfoChip();
  });

  document.addEventListener("click", function (event) {
    if (!activeSymbolLinkGroup) return;
    if (event.target.closest("[data-symbol-link-group]") === activeSymbolLinkGroup) return;
    clearActiveSymbolLinkGroup();
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      clearActiveInfoChip();
      clearActiveSymbolLinkGroup();
    }
  });

  window.addEventListener("resize", function () {
    updateSummaryCardLabels();
    clearActiveInfoChip();
    clearActiveSymbolLinkGroup();
    scheduleChartRelayout(true);
  });
  window.addEventListener("scroll", function () {
    clearActiveInfoChip();
    clearActiveSymbolLinkGroup();
  }, true);
  window.addEventListener("orientationchange", function () {
    updateSummaryCardLabels();
    scheduleChartRelayout(true);
  });
  window.addEventListener("pageshow", function () {
    updateSummaryCardLabels();
    scheduleChartRelayout(true);
  });
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) {
      updateSummaryCardLabels();
      scheduleChartRelayout(true);
    }
  });
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", function () {
      updateSummaryCardLabels();
      scheduleChartRelayout(true);
    });
  }

  scheduleChartRelayout(true);
}());
