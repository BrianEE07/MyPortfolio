(function () {
  const payloadElement = document.getElementById("app-payload");
  const payload = payloadElement ? JSON.parse(payloadElement.textContent || "{}") : {};

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

  function activateTab(tabId) {
    clearActiveInfoChip();
    tabButtons.forEach(function (button) {
      const isActive = button.getAttribute("data-tab-target") === tabId;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-selected", isActive ? "true" : "false");
    });
    tabPanels.forEach(function (panel) {
      panel.classList.toggle("is-active", panel.getAttribute("data-tab-panel") === tabId);
    });
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
  const infoChips = Array.from(document.querySelectorAll(".info-chip[data-tooltip-zh]"));
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

  function setInfoChipExpanded(chip, isExpanded) {
    if (!chip) return;
    chip.setAttribute("aria-expanded", isExpanded ? "true" : "false");
  }

  function positionInfoTooltip(chip) {
    const chipRect = chip.getBoundingClientRect();
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

  function showInfoTooltip(chip) {
    const tooltipText = [chip.dataset.tooltipZh, chip.dataset.tooltipEn]
      .filter(Boolean)
      .join("\n");
    if (!tooltipText) return;

    tooltipElement.textContent = tooltipText;
    tooltipElement.classList.add("is-visible");
    positionInfoTooltip(chip);
  }

  function hideInfoTooltip() {
    tooltipElement.classList.remove("is-visible");
  }

  function clearActiveInfoChip() {
    setInfoChipExpanded(activeInfoChip, false);
    activeInfoChip = null;
    hideInfoTooltip();
  }

  function setActiveInfoChip(chip) {
    if (activeInfoChip && activeInfoChip !== chip) {
      setInfoChipExpanded(activeInfoChip, false);
    }
    activeInfoChip = chip;
    setInfoChipExpanded(activeInfoChip, true);
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

  function updateRankBadges(shouldHighlightTopHoldings) {
    if (!detailTableBody) return;
    const rows = Array.from(detailTableBody.querySelectorAll("tr"));
    rows.forEach(function (row, index) {
      const rankElement = row.querySelector(".symbol-rank");
      if (!rankElement) return;
      rankElement.textContent = String(index + 1);
      rankElement.classList.remove("is-top-1", "is-top-2", "is-top-3");
      if (!shouldHighlightTopHoldings) return;
      if (index === 0) rankElement.classList.add("is-top-1");
      if (index === 1) rankElement.classList.add("is-top-2");
      if (index === 2) rankElement.classList.add("is-top-3");
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
    updateRankBadges(sortKey === defaultSortKey && direction === defaultSortDirection);
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

  infoChips.forEach(function (chip) {
    setInfoChipExpanded(chip, false);
    chip.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      toggleActiveInfoChip(chip);
    });
    chip.addEventListener("mousedown", function (event) {
      event.preventDefault();
      event.stopPropagation();
    });
    chip.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        event.stopPropagation();
        toggleActiveInfoChip(chip);
      }
    });
    chip.addEventListener("mouseenter", function () {
      if (activeInfoChip && activeInfoChip !== chip) return;
      showInfoTooltip(chip);
    });
    chip.addEventListener("mouseleave", function () {
      if (activeInfoChip === chip) return;
      hideInfoTooltip();
    });
    chip.addEventListener("focus", function () {
      if (activeInfoChip && activeInfoChip !== chip) return;
      showInfoTooltip(chip);
    });
    chip.addEventListener("blur", function () {
      if (activeInfoChip === chip) return;
      hideInfoTooltip();
    });
  });

  document.addEventListener("click", function (event) {
    if (!activeInfoChip) return;
    if (event.target.closest(".info-chip") === activeInfoChip) return;
    clearActiveInfoChip();
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      clearActiveInfoChip();
    }
  });

  window.addEventListener("resize", clearActiveInfoChip);
  window.addEventListener("scroll", clearActiveInfoChip, true);

  if (window.Chart && payload.holdingsChart && payload.holdingsChart.labels && payload.holdingsChart.labels.length) {
    const holdingsCanvas = document.getElementById("holdingsChart");
    if (holdingsCanvas) {
      new Chart(holdingsCanvas, {
        type: "doughnut",
        data: {
          labels: payload.holdingsChart.labels,
          datasets: [
            {
              data: payload.holdingsChart.data,
              backgroundColor: ["#b86a17", "#d08a3e", "#e6b780", "#cfc7b8", "#7b8591", "#5d6773", "#a8927d", "#cab39c", "#91550f", "#dfc6a9"],
              borderWidth: 0
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: "bottom",
              labels: {
                boxWidth: 12,
                padding: 18
              }
            }
          }
        }
      });
    }
  }

  if (window.Chart && payload.fearGreedChart && payload.fearGreedChart.labels && payload.fearGreedChart.labels.length) {
    const fearGreedCanvas = document.getElementById("fearGreedChart");
    if (fearGreedCanvas) {
      new Chart(fearGreedCanvas, {
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
  }
}());
