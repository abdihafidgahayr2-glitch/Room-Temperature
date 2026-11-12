// Dashboard: loads readings from the API every 10 seconds and draws the graph

const chart = new Chart(document.getElementById("readings-chart"), {
  type: "line",
  data: {
    labels: [],
    datasets: [
      { label: "Temperature (°C)", data: [], borderColor: "#e67e22", yAxisID: "y", tension: 0.3, pointRadius: 0 },
      { label: "Humidity (%)", data: [], borderColor: "#527c9f", yAxisID: "y1", tension: 0.3, pointRadius: 0 },
    ],
  },
  options: {
    animation: false,
    scales: {
      y: { position: "left", title: { display: true, text: "°C" } },
      y1: { position: "right", title: { display: true, text: "%" }, grid: { drawOnChartArea: false } },
    },
  },
});

async function getJson(url, options) {
  const response = await fetch(url, options);
  if (response.status === 401) {
    window.location.href = "/login";
    return null;
  }
  return response;
}

function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

async function loadReadings() {
  const response = await getJson("/api/sensor_readings?hours=24");
  if (!response || !response.ok) return;
  const readings = await response.json();

  const temperatures = readings.filter((r) => r.sensor === "temperature");
  const humidities = readings.filter((r) => r.sensor === "humidity");

  chart.data.labels = temperatures.map((r) => formatTime(r.date_timestamp));
  chart.data.datasets[0].data = temperatures.map((r) => r.content);
  chart.data.datasets[1].data = humidities.map((r) => r.content);
  chart.update();

  if (temperatures.length) {
    const latest = temperatures[temperatures.length - 1];
    document.getElementById("temperature").textContent = latest.content.toFixed(1) + " °C";
    document.getElementById("last-updated").textContent =
      "Last reading: " + new Date(latest.date_timestamp).toLocaleString();
  }
  if (humidities.length) {
    const latest = humidities[humidities.length - 1];
    document.getElementById("humidity").textContent = latest.content.toFixed(0) + " %";
  }
}

async function loadWindow() {
  const response = await getJson("/api/window");
  if (!response || !response.ok) return;
  const window_status = await response.json();
  const element = document.getElementById("window-state");
  element.textContent = window_status.state;
  element.className = "reading-value window-" + window_status.state;
}

async function refresh() {
  await loadReadings();
  await loadWindow();
}

// Manual open / close buttons
document.querySelectorAll("[data-window-action]").forEach((button) => {
  button.addEventListener("click", async () => {
    const action = button.getAttribute("data-window-action");
    const response = await getJson("/api/window", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: action }),
    });
    if (!response) return;
    const message = document.getElementById("window-message");
    if (response.ok) {
      message.textContent = `Sent "${action}" to the Raspberry Pi`;
    } else {
      const error = await response.json();
      message.textContent = error.detail;
    }
    setTimeout(loadWindow, 1500);
  });
});

// Threshold settings form
document.getElementById("settings-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const response = await getJson("/api/settings", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      open_at: parseFloat(form.get("open_at")),
      close_at: parseFloat(form.get("close_at")),
    }),
  });
  if (!response) return;
  const message = document.getElementById("settings-message");
  if (response.ok) {
    message.textContent = "Saved";
  } else {
    const error = await response.json();
    message.textContent = typeof error.detail === "string" ? error.detail : "Invalid values";
  }
});

refresh();
setInterval(refresh, 10000);
