(function () {
  const payloadElement = document.getElementById("app-payload");
  const payload = payloadElement ? JSON.parse(payloadElement.textContent || "{}") : {};
  const holdingsCanvas = document.getElementById("holdingsChart");
  const holdingsLegend = document.getElementById("holdingsChartLegend");
  const fearGreedCanvas = document.getElementById("fearGreedChart");
  const sp500TrendCanvas = document.getElementById("sp500TrendChart");
  const fearGreedGauge = document.querySelector(".fear-greed-gauge");
  const floatingTabsShell = document.querySelector(".tabs-floating-shell");
  const roadmapTrigger = document.getElementById("roadmapTrigger");
  const roadmapOverlay = document.getElementById("projectRoadmapOverlay");
  const roadmapDialog = document.getElementById("projectRoadmap");

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
    document.querySelectorAll("[data-tooltip-zh]")
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
  let gaugeNeedleAnimationFrame = null;
  let chartRelayoutRequestId = 0;
  let activeCategoryFilter = "all";
  let activeTabId = "overview";
  let floatingTabsHideTimeoutId = null;
  let roadmapRestoreFocusTarget = null;

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

  function clampNumber(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function easeOutCubic(progress) {
    return 1 - Math.pow(1 - progress, 3);
  }

  function scoreToGaugeAngle(score) {
    return 180 - (score / 100) * 180;
  }

  function gaugeLevelForScore(score) {
    if (score < 25) return "extreme-fear";
    if (score < 45) return "fear";
    if (score < 56) return "neutral";
    if (score < 76) return "greed";
    return "extreme-greed";
  }

  function updateFearGreedGaugeActiveState(score) {
    if (!fearGreedGauge) return;

    const activeLevel = gaugeLevelForScore(clampNumber(score, 0, 100));
    const segments = Array.from(fearGreedGauge.querySelectorAll(".fear-greed-segment"));
    const ranges = Array.from(
      fearGreedGauge.parentElement
        ? fearGreedGauge.parentElement.querySelectorAll(".fear-greed-ranges > div")
        : []
    );
    const levelClasses = [
      "extreme-fear",
      "fear",
      "neutral",
      "greed",
      "extreme-greed"
    ];

    segments.forEach(function (segment) {
      segment.classList.toggle("is-active", segment.classList.contains("is-" + activeLevel));
    });
    ranges.forEach(function (range, index) {
      range.classList.toggle("is-active", levelClasses[index] === activeLevel);
    });
  }

  function animateFearGreedNeedle() {
    if (!fearGreedGauge) return;

    const pointer = fearGreedGauge.querySelector(".fear-greed-gauge-pointer");
    const hub = fearGreedGauge.querySelector(".fear-greed-gauge-hub");
    if (!pointer || !hub) return;

    const rawScore = Number(fearGreedGauge.dataset.score);
    if (!Number.isFinite(rawScore)) return;

    const score = clampNumber(rawScore, 0, 100);
    const centerX = Number(hub.getAttribute("cx") || pointer.getAttribute("x1") || 160);
    const centerY = Number(hub.getAttribute("cy") || pointer.getAttribute("y1") || 150);
    const initialX2 = Number(pointer.getAttribute("x2") || centerX);
    const initialY2 = Number(pointer.getAttribute("y2") || centerY - 106);
    const needleLength = Math.hypot(initialX2 - centerX, initialY2 - centerY) || 106;

    function setNeedleByAngle(angle) {
      const radian = angle * Math.PI / 180;
      const x2 = centerX + Math.cos(radian) * needleLength;
      const y2 = centerY - Math.sin(radian) * needleLength;

      pointer.setAttribute("x1", centerX.toFixed(2));
      pointer.setAttribute("y1", centerY.toFixed(2));
      pointer.setAttribute("x2", x2.toFixed(2));
      pointer.setAttribute("y2", y2.toFixed(2));
    }

    const startAngle = 180;
    const targetAngle = scoreToGaugeAngle(score);
    const durationMs = 1400;

    if (gaugeNeedleAnimationFrame) {
      window.cancelAnimationFrame(gaugeNeedleAnimationFrame);
      gaugeNeedleAnimationFrame = null;
    }

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setNeedleByAngle(targetAngle);
      updateFearGreedGaugeActiveState(score);
      return;
    }

    setNeedleByAngle(startAngle);
    updateFearGreedGaugeActiveState(0);
    const startTime = window.performance.now();

    function step(now) {
      const progress = clampNumber((now - startTime) / durationMs, 0, 1);
      const easedProgress = easeOutCubic(progress);
      const currentAngle = startAngle + (targetAngle - startAngle) * easedProgress;
      const currentScore = score * easedProgress;
      setNeedleByAngle(currentAngle);
      updateFearGreedGaugeActiveState(currentScore);

      if (progress < 1) {
        gaugeNeedleAnimationFrame = window.requestAnimationFrame(step);
        return;
      }

      gaugeNeedleAnimationFrame = null;
      setNeedleByAngle(targetAngle);
      updateFearGreedGaugeActiveState(score);
    }

    gaugeNeedleAnimationFrame = window.requestAnimationFrame(step);
  }

  function resetFearGreedNeedleToStart() {
    if (!fearGreedGauge) return;

    const pointer = fearGreedGauge.querySelector(".fear-greed-gauge-pointer");
    const hub = fearGreedGauge.querySelector(".fear-greed-gauge-hub");
    if (!pointer || !hub) return;

    const centerX = Number(hub.getAttribute("cx") || pointer.getAttribute("x1") || 160);
    const centerY = Number(hub.getAttribute("cy") || pointer.getAttribute("y1") || 150);
    const currentX2 = Number(pointer.getAttribute("x2") || centerX);
    const currentY2 = Number(pointer.getAttribute("y2") || centerY - 106);
    const needleLength = Math.hypot(currentX2 - centerX, currentY2 - centerY) || 106;
    const startAngle = 180;
    const radian = startAngle * Math.PI / 180;
    const startX2 = centerX + Math.cos(radian) * needleLength;
    const startY2 = centerY - Math.sin(radian) * needleLength;

    if (gaugeNeedleAnimationFrame) {
      window.cancelAnimationFrame(gaugeNeedleAnimationFrame);
      gaugeNeedleAnimationFrame = null;
    }

    pointer.setAttribute("x1", centerX.toFixed(2));
    pointer.setAttribute("y1", centerY.toFixed(2));
    pointer.setAttribute("x2", startX2.toFixed(2));
    pointer.setAttribute("y2", startY2.toFixed(2));
    updateFearGreedGaugeActiveState(0);
  }

  function shouldAutoHideFloatingTabs() {
    return window.matchMedia("(max-width: 1024px)").matches;
  }

  function isNearPageBottom() {
    const scrollElement = document.scrollingElement || document.documentElement;
    if (!scrollElement) return false;
    return scrollElement.scrollTop + window.innerHeight >= scrollElement.scrollHeight - 56;
  }

  function setFloatingTabsHidden(shouldHide) {
    if (!floatingTabsShell) return;
    floatingTabsShell.classList.toggle("is-auto-hidden", shouldHide);
  }

  function scheduleFloatingTabsAutoHide() {
    if (!floatingTabsShell) return;
    if (floatingTabsHideTimeoutId) {
      window.clearTimeout(floatingTabsHideTimeoutId);
      floatingTabsHideTimeoutId = null;
    }

    setFloatingTabsHidden(false);

    if (!shouldAutoHideFloatingTabs() || isNearPageBottom()) {
      return;
    }

    floatingTabsHideTimeoutId = window.setTimeout(function () {
      setFloatingTabsHidden(!isNearPageBottom());
      floatingTabsHideTimeoutId = null;
    }, 2000);
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

  const verticalHoverLinePlugin = {
    id: "verticalHoverLine",
    afterDraw: function (chart, args, pluginOptions) {
      const activeElements = chart.tooltip && chart.tooltip.getActiveElements
        ? chart.tooltip.getActiveElements()
        : [];
      const activeElement = activeElements[0] || null;
      const tooltipX = chart.tooltip && typeof chart.tooltip.caretX === "number"
        ? chart.tooltip.caretX
        : null;
      if (!activeElement && tooltipX === null) return;

      const x = activeElement && activeElement.element ? activeElement.element.x : tooltipX;
      const chartArea = chart.chartArea;
      if (!chartArea) return;

      const context = chart.ctx;
      context.save();
      context.beginPath();
      context.moveTo(Math.round(x) + 0.5, chartArea.top);
      context.lineTo(Math.round(x) + 0.5, chartArea.bottom);
      context.lineWidth = pluginOptions && pluginOptions.lineWidth ? pluginOptions.lineWidth : 1;
      context.strokeStyle = pluginOptions && pluginOptions.color
        ? pluginOptions.color
        : "rgba(84, 73, 61, 0.22)";
      context.stroke();
      context.restore();
    }
  };

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
    const chartData = payload.fearGreedChart.data || [];
    const shouldAnimate = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const initialData = shouldAnimate ? chartData.map(function () { return 0; }) : chartData;

    const chart = new Chart(fearGreedCanvas, {
      type: "line",
      plugins: [verticalHoverLinePlugin],
      data: {
        labels: payload.fearGreedChart.labels,
        datasets: [
          {
            label: "Fear & Greed",
            data: initialData,
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
        animation: {
          duration: 900,
          easing: "easeOutCubic"
        },
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
            max: 100,
            ticks: {
              stepSize: 20
            }
          }
        },
        plugins: {
          verticalHoverLine: {
            color: "rgba(84, 73, 61, 0.22)"
          },
          legend: {
            display: false
          },
          tooltip: {
            boxPadding: 4,
            bodySpacing: 4,
            titleSpacing: 4,
            padding: 10,
            callbacks: {
              title: function (context) {
                const firstItem = context && context[0];
                return firstItem ? firstItem.label : "";
              }
            }
          }
        }
      }
    });

    if (shouldAnimate) {
      window.requestAnimationFrame(function () {
        window.requestAnimationFrame(function () {
          if (!chart.canvas || !chart.canvas.isConnected) return;
          chart.data.datasets[0].data = chartData;
          chart.update();
        });
      });
    }

    return chart;
  }

  function createSp500TrendChart() {
    if (!hasChartData(payload.sp500TrendChart) || !isCanvasRenderable(sp500TrendCanvas)) {
      return null;
    }

    const trendTone = payload.sp500TrendChart.tone || "gain";
    const trendColor = trendTone === "loss"
      ? "#d85f55"
      : trendTone === "warning"
        ? "#c89124"
        : "#2fbf78";
    const trendFill = trendTone === "loss"
      ? "rgba(216, 95, 85, 0.12)"
      : trendTone === "warning"
        ? "rgba(200, 145, 36, 0.12)"
        : "rgba(47, 191, 120, 0.12)";

    return new Chart(sp500TrendCanvas, {
      type: "line",
      plugins: [verticalHoverLinePlugin],
      data: {
        labels: payload.sp500TrendChart.labels,
        datasets: [
          {
            label: "S&P 500",
            data: payload.sp500TrendChart.data,
            borderColor: trendColor,
            backgroundColor: trendFill,
            fill: true,
            tension: 0.2,
            pointRadius: 0,
            pointHoverRadius: 3
          },
          {
            label: "20MA",
            data: payload.sp500TrendChart.ma20 || [],
            borderColor: "rgba(200, 145, 36, 0.72)",
            borderDash: [5, 5],
            fill: false,
            tension: 0.18,
            pointRadius: 0,
            pointHoverRadius: 0
          },
          {
            label: "60MA",
            data: payload.sp500TrendChart.ma60 || [],
            borderColor: "rgba(94, 139, 191, 0.52)",
            borderDash: [3, 6],
            fill: false,
            tension: 0.18,
            pointRadius: 0,
            pointHoverRadius: 0
          },
          {
            label: "250MA",
            data: payload.sp500TrendChart.ma250 || [],
            borderColor: "rgba(110, 99, 87, 0.42)",
            fill: false,
            tension: 0.18,
            pointRadius: 0,
            pointHoverRadius: 0
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: 900,
          easing: "easeOutCubic"
        },
        interaction: {
          mode: "index",
          intersect: false
        },
        scales: {
          x: {
            grid: {
              color: "rgba(84, 73, 61, 0.14)"
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
          verticalHoverLine: {
            color: "rgba(84, 73, 61, 0.22)"
          },
          legend: {
            display: true,
            labels: {
              boxWidth: 10,
              boxHeight: 10,
              usePointStyle: true
            }
          },
          tooltip: {
            boxPadding: 4,
            bodySpacing: 4,
            titleSpacing: 4,
            padding: 10
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

  function replayFearGreedNeedleIfPulseVisible() {
    if (activeTabId !== "pulse") return;
    if (!fearGreedGauge || !fearGreedGauge.getClientRects().length) return;
    animateFearGreedNeedle();
  }

  function runChartRelayout(shouldReplayGauge) {
    rebuildOrRefreshCharts();
    if (shouldReplayGauge) {
      replayFearGreedNeedleIfPulseVisible();
    }
  }

  function scheduleChartRelayout(forceRebuild) {
    const shouldReplayGauge = Boolean(forceRebuild);
    const requestId = chartRelayoutRequestId + 1;
    chartRelayoutRequestId = requestId;
    chartRelayoutNeedsRebuild = chartRelayoutNeedsRebuild || Boolean(forceRebuild);
    if (chartRelayoutTimeoutId) {
      window.clearTimeout(chartRelayoutTimeoutId);
      chartRelayoutTimeoutId = null;
    }
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(function () {
        if (requestId !== chartRelayoutRequestId) return;
        if (chartRelayoutTimeoutId) {
          window.clearTimeout(chartRelayoutTimeoutId);
          chartRelayoutTimeoutId = null;
        }
        runChartRelayout(shouldReplayGauge);
      });
    });
    chartRelayoutTimeoutId = window.setTimeout(function () {
      if (requestId !== chartRelayoutRequestId) return;
      chartRelayoutTimeoutId = null;
      runChartRelayout(shouldReplayGauge);
    }, 160);
  }

  function activateTab(tabId) {
    if (activeTabId === "details" && tabId !== "details") {
      applyCategoryFilter("all", true, true, "auto");
    }

    if (tabId === "pulse") {
      resetFearGreedNeedleToStart();
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
    scheduleFloatingTabsAutoHide();
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

  function isRoadmapOpen() {
    return Boolean(roadmapOverlay && !roadmapOverlay.hidden);
  }

  function openRoadmap() {
    if (!roadmapOverlay || !roadmapDialog || isRoadmapOpen()) return;

    roadmapRestoreFocusTarget = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : roadmapTrigger;
    clearActiveInfoChip();
    clearActiveSymbolLinkGroup();
    roadmapOverlay.hidden = false;
    document.body.classList.add("is-roadmap-open");
    if (roadmapTrigger) {
      roadmapTrigger.setAttribute("aria-expanded", "true");
    }

    window.requestAnimationFrame(function () {
      roadmapOverlay.classList.add("is-visible");
      roadmapDialog.focus();
    });
  }

  function closeRoadmap(shouldRestoreFocus) {
    if (!roadmapOverlay || !roadmapDialog || !isRoadmapOpen()) return;

    roadmapOverlay.classList.remove("is-visible");
    document.body.classList.remove("is-roadmap-open");
    if (roadmapTrigger) {
      roadmapTrigger.setAttribute("aria-expanded", "false");
    }

    window.setTimeout(function () {
      if (roadmapOverlay.classList.contains("is-visible")) return;
      roadmapOverlay.hidden = true;
      if (shouldRestoreFocus && roadmapRestoreFocusTarget && roadmapRestoreFocusTarget.focus) {
        roadmapRestoreFocusTarget.focus();
      }
      roadmapRestoreFocusTarget = null;
    }, 180);
  }

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
      .filter(function (text, index, list) {
        return list.indexOf(text) === index;
      })
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

  if (roadmapTrigger) {
    roadmapTrigger.addEventListener("click", function () {
      if (isRoadmapOpen()) {
        closeRoadmap(true);
        return;
      }
      openRoadmap();
    });
  }

  if (roadmapOverlay) {
    roadmapOverlay.addEventListener("click", function (event) {
      if (event.target === roadmapOverlay || event.target.closest("[data-roadmap-close]")) {
        closeRoadmap(true);
      }
    });
  }

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
    if (
      isRoadmapOpen()
      && roadmapDialog
      && !roadmapDialog.contains(event.target)
      && event.target !== roadmapTrigger
    ) {
      closeRoadmap(false);
      return;
    }

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
      if (isRoadmapOpen()) {
        closeRoadmap(true);
        return;
      }
      clearActiveInfoChip();
      clearActiveSymbolLinkGroup();
    }
  });

  window.addEventListener("resize", function () {
    updateSummaryCardLabels();
    clearActiveInfoChip();
    clearActiveSymbolLinkGroup();
    scheduleFloatingTabsAutoHide();
    scheduleChartRelayout(true);
  });
  window.addEventListener("scroll", function () {
    clearActiveInfoChip();
    clearActiveSymbolLinkGroup();
    scheduleFloatingTabsAutoHide();
  }, true);
  window.addEventListener("orientationchange", function () {
    updateSummaryCardLabels();
    scheduleFloatingTabsAutoHide();
    scheduleChartRelayout(true);
  });
  window.addEventListener("pageshow", function () {
    updateSummaryCardLabels();
    scheduleFloatingTabsAutoHide();
    scheduleChartRelayout(true);
  });
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) {
      updateSummaryCardLabels();
      scheduleFloatingTabsAutoHide();
      scheduleChartRelayout(true);
    }
  });
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", function () {
      updateSummaryCardLabels();
      scheduleFloatingTabsAutoHide();
      scheduleChartRelayout(true);
    });
  }

  ["touchstart", "touchmove", "pointerdown"].forEach(function (eventName) {
    window.addEventListener(eventName, scheduleFloatingTabsAutoHide, { passive: true });
  });

  scheduleFloatingTabsAutoHide();
  scheduleChartRelayout(true);
}());
