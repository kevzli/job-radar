// Packages Job Radar.app: stages the Python backend and bundles it as a resource.
const fs = require("fs");
const path = require("path");
const { packager } = require("@electron/packager");

const ROOT = path.join(__dirname, "..");
const STAGE = path.join(__dirname, "build", "backend");
const BACKEND_FILES = ["server.py", "scan.py", "sources.py", "scoring.py", "db.py", "common.py", "companies.py", "config.json", "static"];

(async () => {
  fs.rmSync(STAGE, { recursive: true, force: true });
  fs.mkdirSync(STAGE, { recursive: true });
  for (const f of BACKEND_FILES) fs.cpSync(path.join(ROOT, f), path.join(STAGE, f), { recursive: true });

  const [out] = await packager({
    dir: __dirname,
    name: "Job Radar",
    appBundleId: "com.jobradar.app",
    icon: path.join(__dirname, "assets", "icon.icns"),
    extraResource: [STAGE],
    out: path.join(__dirname, "dist"),
    overwrite: true,
    platform: "darwin",
    arch: process.arch,
    ignore: [/^\/build/, /^\/dist/, /^\/build\.js$/, /icon_1024\.png$/],
    extendInfo: { LSUIElement: false },
  });
  console.log("Built " + path.join(out, "Job Radar.app"));
})().catch((e) => { console.error(e); process.exit(1); });
