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
      level === "ok"
        ? "✅"
        : level === "warn"
        ? "⚠️"
        : level === "err"
        ? "❌"
        : "ℹ️";
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
  const scoreThumb = $("scoreThumb");
  const scoreLabel = $("scoreLabel");
  const reportBox = $("reportBox");

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

  // ✅ NEW: real Twilio inbound call → clear feed
  socket.on("call_incoming", (data) => {
    chatFeed.innerHTML = "";
    reportBox.textContent = "Report will appear here after the call ends…";
    setScore(0);
    const from = data && data.from ? data.from : "Unknown number";
    log(`Incoming call from ${from}`, "ok");
    setState("in call"); // or "ringing" if you prefer
  });

  // live transcript + AI suggestions
  socket.on("update", (data) => {
    if (data.caller) appendMsg("caller", data.caller);
    if (data.suggestion) appendMsg("ai", data.suggestion);
  });

  // final call-quality report
  socket.on("call_report", (data) => {
    const text = data.report || "No report available.";
    reportBox.textContent = text;
    const score = extractScore(text);
    setScore(score);
    log(`Quality report received (${score.toFixed(1)}/10)`, "ok");
  });

  // caller hung up / Twilio ended call
  socket.on("call_ended", (data) => {
    log("Hanging up... (caller disconnected)", "warn");
    reset();
  });

  // ---- UI MESSAGES ----
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

  // ---- SCORE EXTRACTION (smart) ----
  function extractScore(text) {
    const match = text.match(/Overall\s*Score[:\s]*([\d.]+)\s*(?:\/\s*(\d+)|%|$)/i);
    if (!match) return 0;

    let value = parseFloat(match[1]);
    const denominator = match[2] ? parseFloat(match[2]) : null;

    if (denominator && denominator > 10) {
      value = (value / denominator) * 10; // 80/100 → 8
    } else if (text.includes("%")) {
      value = value / 10; // 85% → 8.5
    } else if (value > 10) {
      value = value / 10; // 80 → 8
    }

    return Math.max(0, Math.min(10, parseFloat(value.toFixed(1))));
  }

  // ---- SCORE BAR UI (Animated) ----
  function setScore(n) {
    const pct = Math.max(0, Math.min(100, (n / 10) * 100));
    scoreThumb.style.transition = "left 0.8s cubic-bezier(0.4, 0, 0.2, 1)";
    scoreThumb.style.left = `calc(${pct}% - 4px)`;
    scoreLabel.textContent = `${n.toFixed(1)}/10`;

    // if you added the extra score header elements, update them here
    const scoreValue = document.getElementById("scoreValue");
    const scoreRemark = document.getElementById("scoreRemark");
    if (scoreValue && scoreRemark) {
      scoreValue.textContent = n.toFixed(1);
      scoreRemark.textContent =
        n >= 9
          ? "Outstanding"
          : n >= 8
          ? "Excellent"
          : n >= 7
          ? "Good"
          : n >= 6
          ? "Fair"
          : "Needs Improvement";
    }
  }

  // ---- Twilio Device Integration (browser side) ----
  let device = null;
  let conn = null;

  async function initTwilio() {
    try {
      const res = await fetch("/token?identity=agent");
      const data = await res.json();
      device = new Twilio.Device(data.token, {
        codecPreferences: ["opus", "pcmu"],
        enableRingingState: true,
      });
      await device.register();
      log("Twilio Device ready", "ok");
      setState("idle");

      // this path is for browser calls; keep it
      device.on("incoming", (c) => {
        conn = c;
        btnAccept.style.display = "inline-block";
        btnDecline.style.display = "inline-block";
        setState("ringing");

        // reset UI for new call
        chatFeed.innerHTML = "";
        reportBox.textContent = "Report will appear here after the call ends…";
        setScore(0);

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
