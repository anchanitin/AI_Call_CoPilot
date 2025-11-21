(() => {
  const $ = (id) => document.getElementById(id);

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

  const chatFeed = $("chatFeed");
  const stateBadge = $("callStateBadge");
  const reportBox = $("reportBox");
  const summaryBox = $("summaryText");
  const metricBox = $("metricBreakdown");
  const badgeBox = $("insightBadges");

  const detailedAnalysisBox = $("detailedAnalysisBox");
  const detailedAnalysisText = $("detailedAnalysisText");
  const strengthsBox = $("strengthsBox");
  const strengthsText = $("strengthsText");
  const areasBox = $("areasBox");
  const areasText = $("areasText");
  const recommendationsBox = $("recommendationsBox");
  const recommendationsText = $("recommendationsText");

  function setState(state) {
    stateBadge.textContent = state;
    stateBadge.className = "badge fade";
    if (state === "ringing") stateBadge.classList.add("state-ringing");
    else if (state === "in call") stateBadge.classList.add("state-live");
    else stateBadge.classList.add("state-idle");
  }

  const socket = io();
  socket.on("connect", () => log("Socket connected", "ok"));
  socket.on("disconnect", () => log("Socket disconnected", "err"));

  socket.on("call_incoming", (data) => {
    chatFeed.innerHTML = "";
    reportBox.style.display = "block";
    reportBox.textContent = "Report will appear here after the call ends…";
    summaryBox.textContent = "Waiting for summary…";
    metricBox.innerHTML = "";
    badgeBox.innerHTML = "";
    hideAllSections();
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
    const summary = extractSummary(text);
    summaryBox.textContent = summary || "Summary not found in report.";

    const metrics = extractSubScores(text);
    renderMetrics(metrics);
    renderBadges(metrics);

    const foundAny = renderDetailedSections(text);
    // hide raw report if detailed boxes are filled
    reportBox.style.display = foundAny ? "none" : "block";
    if (!foundAny) reportBox.textContent = text;

    log("Quality report received", "ok");
  });

  socket.on("call_ended", () => {
    log("Caller disconnected", "warn");
    reset();
  });

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
    const m = text.match(/Summary[:\s]+([\s\S]*?)(?=Detailed|Strengths|Areas|AI Recommendations|$)/i);
    return m ? m[1].trim() : "";
  }

  function extractSubScores(text) {
    const metrics = {};
    const regex = /([A-Za-z& ]{3,40}):\s*(\d{1,3})(?:\s*(?:out\s*of|\/)\s*(\d+))?/gi;
    let match;
    while ((match = regex.exec(text)) !== null) {
      const label = match[1].trim();
      let val = parseFloat(match[2]);
      const denom = match[3] ? parseFloat(match[3]) : null;
      if (denom && denom > 10) val = (val / denom) * 10;
      else if (val > 10) val = val / 10;
      metrics[label] = Math.min(10, Math.max(0, parseFloat(val.toFixed(1))));
    }
    if (!metrics["Overall Score"] && Object.keys(metrics).length > 0) {
      const vals = Object.entries(metrics)
        .filter(([k]) => !/overall/i.test(k))
        .map(([_, v]) => v);
      if (vals.length)
        metrics["Overall Score"] = parseFloat((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1));
    }
    return metrics;
  }

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
      if (/overall/i.test(key)) row.classList.add("metric-overall");
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

  function hideAllSections() {
    [detailedAnalysisBox, strengthsBox, areasBox, recommendationsBox].forEach((el) => {
      el.style.display = "none";
    });
  }

  // ---- NEW: Render four separate boxes ----
  function renderDetailedSections(text) {
    let found = false;
    const sections = {
      detailed: text.match(/Detailed Analysis[:\s]+([\s\S]*?)(?=Strengths|Areas|AI Recommendations|$)/i),
      strengths: text.match(/Strengths[:\s]+([\s\S]*?)(?=Areas|AI Recommendations|$)/i),
      areas: text.match(/Areas for Improvement[:\s]+([\s\S]*?)(?=AI Recommendations|$)/i),
      recommendations: text.match(/AI Recommendations[:\s]+([\s\S]*)/i),
    };

    function formatText(t) {
      if (!t) return "";
      // convert dash bullets into <ul><li> items
      const lines = t
        .split(/\n|-/)
        .map((l) => l.trim())
        .filter((l) => l.length > 0);
      if (lines.length > 1) return "<ul><li>" + lines.join("</li><li>") + "</li></ul>";
      return `<p>${t}</p>`;
    }

    if (sections.detailed && sections.detailed[1].trim()) {
      detailedAnalysisText.innerHTML = formatText(sections.detailed[1].trim());
      detailedAnalysisBox.style.display = "block";
      found = true;
    }
    if (sections.strengths && sections.strengths[1].trim()) {
      strengthsText.innerHTML = formatText(sections.strengths[1].trim());
      strengthsBox.style.display = "block";
      found = true;
    }
    if (sections.areas && sections.areas[1].trim()) {
      areasText.innerHTML = formatText(sections.areas[1].trim());
      areasBox.style.display = "block";
      found = true;
    }
    if (sections.recommendations && sections.recommendations[1].trim()) {
      recommendationsText.innerHTML = formatText(sections.recommendations[1].trim());
      recommendationsBox.style.display = "block";
      found = true;
    }
    return found;
  }
  function reset() {
    setState("idle");
  }

})();







