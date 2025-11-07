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
  }
  applyTheme(localStorage.getItem("theme") || "light");
  themeToggle.onclick = () =>
    applyTheme(root.getAttribute("data-theme") === "light" ? "dark" : "light");

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
    logEl.innerHTML += `[${time}] ${icon} ${msg}<br>`;
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
    stateBadge.className = "badge";
    if (state === "ringing") stateBadge.classList.add("state-ringing");
    else if (state === "in call") stateBadge.classList.add("state-live");
    else stateBadge.classList.add("state-idle");
  }

  // ---- SOCKET IO ----
  const socket = io();
  socket.on("connect", () => log("Socket connected", "ok"));
  socket.on("disconnect", () => log("Socket disconnected", "err"));

  // live transcript + AI suggestions
  socket.on("update", (data) => {
    if (data.caller) appendMsg("caller", data.caller);
    if (data.suggestion) appendMsg("ai", data.suggestion);
  });

  // final call-quality report
  socket.on("call_report", (data) => {
    const text = data.report || "No report available.";
    reportBox.textContent = text;
    setScore(extractScore(text));
    log("Quality report received", "ok");
  });

  // NEW: caller hung up / Twilio ended call
  socket.on("call_ended", (data) => {
  log("Hanging up... (caller disconnected)", "warn");
  reset();
  });


  function appendMsg(role, text) {
    const div = document.createElement("div");
    div.className = `msg ${role} fade`;
    div.textContent = `${role === "caller" ? "Caller" : "AI"}: ${text}`;
    chatFeed.appendChild(div);
    chatFeed.scrollTop = chatFeed.scrollHeight;
  }

  function extractScore(text) {
    const m = text.match(/Overall\s*Score[:\s]+(\d{1,2})/i);
    const raw = m ? parseInt(m[1], 10) : 0;
    return Math.max(0, Math.min(10, raw));
  }

  function setScore(n) {
    const pct = Math.max(0, Math.min(100, (n / 10) * 100));
    scoreThumb.style.left = `calc(${pct}% - 4px)`;
    scoreLabel.textContent = `${n}/10`;
  }

  // ---- Twilio Integration ----
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