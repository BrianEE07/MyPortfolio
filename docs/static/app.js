(function () {
  const payloadElement = document.getElementById("app-payload");
  const payload = payloadElement ? JSON.parse(payloadElement.textContent || "{}") : {};

  function updateThemeToggleText(theme) {
    const valueElement = document.getElementById("themeToggleValue");
    if (!valueElement) return;
    valueElement.textContent = theme === "dark" ? "Dark / 深色" : "Light / 淺色";
  }

  function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    updateThemeToggleText(theme);
    try {
      localStorage.setItem("portfolio-theme", theme);
    } catch (error) {
      // Ignore storage failures and keep the in-memory theme.
    }
  }

  const themeToggle = document.getElementById("themeToggle");
  const initialTheme = document.documentElement.getAttribute("data-theme") || "light";
  updateThemeToggleText(initialTheme);

  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
      setTheme(currentTheme === "dark" ? "light" : "dark");
    });
  }

  const tabButtons = Array.from(document.querySelectorAll("[data-tab-target]"));
  const tabPanels = Array.from(document.querySelectorAll("[data-tab-panel]"));

  function activateTab(tabId) {
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

  activateTab("overview");

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
