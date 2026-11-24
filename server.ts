import { spawn } from "node:child_process";
import http from "node:http";
import path from "node:path";
import express from "express";
import type { Request, Response } from "express";

const PORT = Number(process.env.PORT || 3000);
const PY_PORT = 5001;
const ROOT_DIR = process.cwd();
const FRONTEND_DIR = path.join(ROOT_DIR, "VayuMitra", "frontend");
const PY_APP = path.join(ROOT_DIR, "VayuMitra", "backend", "app.py");

const pyProc = spawn("python3", [PY_APP, "--stdlib", "--host", "127.0.0.1", "--port", String(PY_PORT)], {
  cwd: path.join(ROOT_DIR, "VayuMitra", "backend"),
  stdio: "inherit",
});

pyProc.on("error", (err) => {
  console.error("Failed to start Python backend:", err);
});

const shutdown = () => {
  if (!pyProc.killed) {
    pyProc.kill("SIGTERM");
  }
  process.exit(0);
};
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

function proxyToPython(req: Request, res: Response): void {
  const options: http.RequestOptions = {
    hostname: "127.0.0.1",
    port: PY_PORT,
    path: req.originalUrl,
    method: req.method,
    headers: {
      ...req.headers,
      host: `127.0.0.1:${PY_PORT}`,
    },
  };

  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
    proxyRes.pipe(res, { end: true });
  });

  proxyReq.on("error", (err) => {
    if (!res.headersSent) {
      res.status(502).json({ error: `Backend unavailable: ${err.message}` });
    }
  });

  req.pipe(proxyReq, { end: true });
}

const app = express();

app.use("/api", proxyToPython);
app.use("/uploads", proxyToPython);

app.use(express.static(FRONTEND_DIR, { extensions: ["html"] }));

app.get("/", (_req: Request, res: Response) => {
  res.sendFile(path.join(FRONTEND_DIR, "index.html"));
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`VayuMitra server listening on http://0.0.0.0:${PORT}`);
});
