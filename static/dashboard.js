(() => {
  const $ = (id) => document.getElementById(id);

  // ---- THEME TOGGLE ----
  const root = document.documentElement;
  const themeToggle = $("themeToggle");
  const themeLabel = $("themeLabel");

  function applyTheme(mode) {
    root.setAttribute("data-theme", mode);
    themeLabel.textContent = mode === "light" ? "Dark" : "Light";
    localStorage.setItem("theme", mode);
    root.style.transition = "background-color 0.4s ease, color 0.4s ease";
  }
  applyTheme(localStorage.getItem("theme") || "light");
  themeToggle.onclick = () => {
    const next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
    applyTheme(next);
  };

  // ---- LOGGING ----
  const logEl = $("events");
  function log(msg, level = "ok") {
    const time = new Date().toLocaleTimeString();
    const icon =
      level === "ok" ? "✅" : level === "warn" ? "⚠️" : level === "err" ? "❌" : "ℹ️";
    const line = document.createElement("div");
    line.innerHTML = `[${time}] ${icon} ${msg}`;
    line.style.opacity = 0;
    line.style.transition = "opacity 0.4s ease";
    logEl.appendChild(line);
    requestAnimationFrame(() => (line.style.opacity = 1));
    logEl.scrollTop = logEl.scrollHeight;
  }

  // ---- ELEMENTS ----
  const chatFeed = $("chatFeed");
  const btnAccept = $("btnAccept");
  const btnDecline = $("btnDecline");
  const btnHang = $("btnHangup");
  const stateBadge = $("callStateBadge");
  const reportBox = $("reportBox");
  const summaryBox = $("summaryText");
  const metricBox = $("metricBreakdown");
  const badgeBox = $("insightBadges");

  function setState(state) {
    stateBadge.textContent = state;
    stateBadge.className = "badge fade";
    if (state === "ringing") stateBadge.classList.add("state-ringing");
    else if (state === "in call") stateBadge.classList.add("state-live");
    else stateBadge.classList.add("state-idle");
  }

  // ---- SOCKET IO ----
  const socket = io();
  socket.on("connect", () => log("Socket connected", "ok"));
  socket.on("disconnect", () => log("Socket disconnected", "err"));

  socket.on("call_incoming", (data) => {
    chatFeed.innerHTML = "";
    reportBox.textContent = "Report will appear here after the call ends…";
    summaryBox.textContent = "Waiting for summary…";
    metricBox.innerHTML = "";
    badgeBox.innerHTML = "";
    const from = data && data.from ? data.from : "Unknown number";
    log(`Incoming call from ${from}`, "ok");
    setState("in call");
  });

  socket.on("update", (data) => {
    if (data.caller) appendMsg("caller", data.caller);
    if (data.suggestion) appendMsg("ai", data.suggestion);
  });

  socket.on("call_report", (data) => {
    const text = data.report || "No report available.";
    reportBox.textContent = text;

    const summary = extractSummary(text);
    summaryBox.textContent = summary || "Summary not found in report.";

    const metrics = extractSubScores(text);
    renderMetrics(metrics);
    renderBadges(metrics);

    log("Quality report received", "ok");
  });

  socket.on("call_ended", () => {
    log("Hanging up... (caller disconnected)", "warn");
    reset();
  });

  // ---- UI HELPERS ----
  function appendMsg(role, text) {
    const div = document.createElement("div");
    div.className = `msg ${role}`;
    div.textContent = `${role === "caller" ? "Caller" : "AI"}: ${text}`;
    div.style.opacity = 0;
    div.style.transition = "opacity 0.5s ease";
    chatFeed.appendChild(div);
    requestAnimationFrame(() => (div.style.opacity = 1));
    chatFeed.scrollTop = chatFeed.scrollHeight;
  }

  function extractSummary(text) {
    const m = text.match(/Summary[:\s]+([\s\S]*?)(?=Detailed|Strengths|Areas|Improvements|AI Recommendations|$)/i);
    return m ? m[1].trim() : "";
  }

  // ✅ Fixed normalization for “Overall Score: 85 out of 100” vs 10/10 mismatch
  function extractSubScores(text) {
    const metrics = {};
    const regex = /([A-Za-z& ]{3,40}):\s*(\d{1,3})(?:\s*(?:out\s*of|\/)\s*(\d+))?/gi;
    let match;

    while ((match = regex.exec(text)) !== null) {
      const label = match[1].trim();
      let val = parseFloat(match[2]);
      const denom = match[3] ? parseFloat(match[3]) : null;

      // Normalize to /10 scale
      if (denom && denom > 10) val = (val / denom) * 10;
      else if (text.includes("%") && val > 10) val = val / 10;
      else if (val > 10) val = val / 10;

      // Preserve proper precision
      metrics[label] = Math.min(10, Math.max(0, parseFloat(val.toFixed(1))));
    }

    // 🧩 If overall missing, average others
    if (!metrics["Overall Score"] && Object.keys(metrics).length > 0) {
      const vals = Object.entries(metrics)
        .filter(([k]) => !/overall/i.test(k))
        .map(([_, v]) => v);
      if (vals.length) {
        metrics["Overall Score"] = parseFloat((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1));
      }
    }

    return metrics;
  }

  // ✅ Highlight and align overall row
  function renderMetrics(metrics) {
    metricBox.innerHTML = "";
    const entries = Object.entries(metrics);
    if (!entries.length) {
      metricBox.innerHTML = "<div class='metric-empty'>No detailed metrics provided.</div>";
      return;
    }
    entries.forEach(([key, val]) => {
      const row = document.createElement("div");
      row.className = "metric-bar";
      if (/overall/i.test(key)) row.classList.add("metric-overall"); // highlight row
      row.innerHTML = `
        <span class="metric-label">${key}</span>
        <div class="metric-progress"><div style="width:${val * 10}%"></div></div>
        <span class="metric-score">${val.toFixed(1)}/10 (${(val * 10).toFixed(0)}%)</span>
      `;
      metricBox.appendChild(row);
    });
  }

  function renderBadges(metrics) {
    badgeBox.innerHTML = "";
    const entries = Object.entries(metrics);
    if (!entries.length) return;
    entries.forEach(([key, val]) => {
      const badge = document.createElement("span");
      badge.className = "insight-badge";
      if (val >= 9) {
        badge.textContent = `🌟 Excellent ${key}`;
        badge.classList.add("good");
      } else if (val >= 7) {
        badge.textContent = `👍 Good ${key}`;
      } else {
        badge.textContent = `⚠️ Improve ${key}`;
        badge.classList.add("warn");
      }
      badgeBox.appendChild(badge);
    });
  }

  // ---- TWILIO DEVICE ----
  let device = null, conn = null;
  async function initTwilio() {
    try {
      const res = await fetch("/token?identity=agent");
      const data = await res.json();
      device = new Twilio.Device(data.token, { codecPreferences: ["opus", "pcmu"], enableRingingState: true });
      await device.register();
      log("Twilio Device ready", "ok");
      setState("idle");

      device.on("incoming", (c) => {
        conn = c;
        btnAccept.style.display = "inline-block";
        btnDecline.style.display = "inline-block";
        setState("ringing");

        chatFeed.innerHTML = "";
        reportBox.textContent = "Report will appear here after the call ends…";
        summaryBox.textContent = "Waiting for summary…";
        metricBox.innerHTML = "";
        badgeBox.innerHTML = "";

        btnAccept.onclick = () => {
          log("Accepting call...", "ok");
          c.accept();
          btnAccept.style.display = "none";
          btnDecline.style.display = "none";
          btnHang.disabled = false;
          setState("in call");
        };
        btnDecline.onclick = () => {
          log("Declined call", "warn");
          c.reject();
          reset();
        };
      });

      device.on("disconnect", () => {
        log("Call ended (device disconnect)", "warn");
        reset();
      });
    } catch (err) {
      log(`Error: ${err.message}`, "err");
    }
  }

  function reset() {
    btnHang.disabled = true;
    btnAccept.style.display = "none";
    btnDecline.style.display = "none";
    setState("idle");
  }

  btnHang.onclick = () => {
    if (conn) {
      log("Hanging up...", "warn");
      conn.disconnect();
      reset();
    }
  };

  initTwilio();
})();
