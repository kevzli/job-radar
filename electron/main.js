// Job Radar desktop app: runs the Python scanner/server in the background and
// shows the dashboard in a native window. Closing the window keeps the app in
// the menu bar so the every-two-weeks scan still happens.
const { app, BrowserWindow, Tray, Menu, shell, nativeImage, dialog, nativeTheme } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const http = require("http");
const path = require("path");

const PORT = 8787;
const BASE = `http://127.0.0.1:${PORT}`;
// In the packaged app the Python sources ship in Resources/backend; in dev they sit one folder up.
const BACKEND = app.isPackaged ? path.join(process.resourcesPath, "backend") : path.join(__dirname, "..");
const DATA = path.join(app.getPath("userData"), "data");

let win = null, tray = null, server = null, quitting = false;

if (!app.requestSingleInstanceLock()) app.quit();
app.on("second-instance", () => showWindow());

function get(urlPath) {
  return new Promise((resolve, reject) => {
    const req = http.get(BASE + urlPath, (res) => {
      let body = "";
      res.on("data", (c) => (body += c));
      res.on("end", () => (res.statusCode === 200 ? resolve(body) : reject(new Error("HTTP " + res.statusCode))));
    });
    req.on("error", reject);
    req.setTimeout(3000, () => req.destroy(new Error("timeout")));
  });
}

function post(urlPath) {
  return new Promise((resolve) => {
    const req = http.request(BASE + urlPath, { method: "POST" }, (res) => { res.resume(); res.on("end", resolve); });
    req.on("error", resolve);
    req.end("{}");
  });
}

async function serverUp() {
  try { return JSON.parse(await get("/api/status")).config !== undefined; } catch { return false; }
}

async function startServer() {
  if (await serverUp()) return; // already running (e.g. installed via install.sh)
  fs.mkdirSync(DATA, { recursive: true });
  const log = fs.openSync(path.join(DATA, "server.log"), "a");
  server = spawn("/usr/bin/python3", [path.join(BACKEND, "server.py")], {
    cwd: BACKEND,
    env: { ...process.env, JOBRADAR_DATA: DATA, PORT: String(PORT), PYTHONUNBUFFERED: "1" },
    stdio: ["ignore", log, log],
  });
  server.on("exit", (code) => {
    server = null;
    if (!quitting) {
      dialog.showErrorBox("Job Radar", `The background scanner stopped (exit code ${code}). See ${path.join(DATA, "server.log")}.`);
    }
  });
  for (let i = 0; i < 60; i++) {
    if (await serverUp()) return;
    await new Promise((r) => setTimeout(r, 250));
  }
  throw new Error("Server did not start. See " + path.join(DATA, "server.log"));
}

function showWindow() {
  if (!win) createWindow();
  win.show();
  win.focus();
  if (process.platform === "darwin") app.dock.show();
}

function createWindow() {
  win = new BrowserWindow({
    width: 980, height: 820, minWidth: 420, minHeight: 480,
    title: "Job Radar",
    titleBarStyle: "hidden",
    trafficLightPosition: { x: 18, y: 19 },
    backgroundColor: nativeTheme.shouldUseDarkColors ? "#111215" : "#fbfbfc",
    show: false,
    webPreferences: { contextIsolation: true, sandbox: true },
  });
  win.loadURL(BASE + "/");
  win.once("ready-to-show", () => win.show());
  // Job links open in the default browser instead of inside the app.
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: "deny" }; });
  win.webContents.on("will-navigate", (e, url) => {
    if (!url.startsWith(BASE)) { e.preventDefault(); shell.openExternal(url); }
  });
  win.on("close", (e) => {
    if (!quitting) { e.preventDefault(); win.hide(); if (process.platform === "darwin") app.dock.hide(); }
  });
}

function buildTray() {
  const icon = nativeImage.createFromPath(path.join(__dirname, "assets", "trayTemplate.png"));
  icon.setTemplateImage(true);
  tray = new Tray(icon);
  tray.setToolTip("Job Radar");
  const refresh = () => {
    const login = app.getLoginItemSettings().openAtLogin;
    tray.setContextMenu(Menu.buildFromTemplate([
      { label: "Open Job Radar", click: showWindow },
      { label: "Scan Now", click: async () => { await post("/api/scan"); showWindow(); } },
      { label: "Open Latest Digest", click: () => shell.openExternal(BASE + "/digest") },
      { type: "separator" },
      { label: "Open Settings Folder", click: () => shell.openPath(DATA) },
      { label: "Launch at Login", type: "checkbox", checked: login, click: (m) => { app.setLoginItemSettings({ openAtLogin: m.checked, openAsHidden: true }); refresh(); } },
      { type: "separator" },
      { label: "Quit Job Radar", click: () => { quitting = true; app.quit(); } },
    ]));
  };
  refresh();
}

function buildMenu() {
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    { role: "appMenu" },
    { label: "Jobs", submenu: [
      { label: "Scan Now", accelerator: "CmdOrCtrl+R", click: () => post("/api/scan").then(() => win && win.reload()) },
      { label: "Reload", accelerator: "CmdOrCtrl+Shift+R", click: () => win && win.reload() },
      { label: "Open Settings Folder", click: () => shell.openPath(DATA) },
    ] },
    { role: "editMenu" },
    { role: "windowMenu" },
  ]));
}

app.whenReady().then(async () => {
  // Turn on launch-at-login the first time, so the biweekly scan keeps running.
  const flag = path.join(app.getPath("userData"), ".first-run-done");
  if (app.isPackaged && !process.env.JOBRADAR_NO_LOGIN_ITEM && !fs.existsSync(flag)) {
    app.setLoginItemSettings({ openAtLogin: true, openAsHidden: true });
    fs.mkdirSync(path.dirname(flag), { recursive: true });
    fs.writeFileSync(flag, "");
  }
  buildMenu();
  buildTray();
  try {
    await startServer();
  } catch (e) {
    dialog.showErrorBox("Job Radar", String(e.message || e));
    quitting = true;
    return app.quit();
  }
  if (!app.getLoginItemSettings().wasOpenedAsHidden) showWindow();
  else if (process.platform === "darwin") app.dock.hide();
});

app.on("activate", showWindow);
app.on("before-quit", () => { quitting = true; });
app.on("window-all-closed", () => {}); // stay alive in the menu bar
app.on("will-quit", () => { if (server) server.kill(); });
