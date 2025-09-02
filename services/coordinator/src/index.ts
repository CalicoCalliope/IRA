import "dotenv/config";
import express, { Request, Response } from "express";
import { z } from "zod";

// Configuration
const PORT = Number(process.env.PORT || 8000);
const EMBEDDER_URL = process.env.EMBEDDER_URL || "http://127.0.0.1:8001";

// Helpers
async function withTimeout<T>(p: Promise<T>, ms = 10000): Promise<T> {
  const t = new Promise<never>((_, rej) => setTimeout(() => rej(new Error("timeout")), ms));
  return Promise.race([p, t]);
}

async function fetchJSON(url: string, init?: RequestInit) {
  const res = await withTimeout(fetch(url, init));
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText} - ${body}`);
  }
  return res.json();
}

// App
const app = express();
app.use(express.json({ limit: "512kb" }));

// GET /health - returns embedder health plus coordinator info
app.get("/health", async (_req: Request, res: Response) => {
  try {
    const health = await fetchJSON(`${EMBEDDER_URL}/health`);
    return res.json({
      coordinator: { ok: true, embedderUrl: EMBEDDER_URL },
      embedder: health
    });
  } catch (err: any) {
    return res.status(503).json({
      coordinator: { ok: false, embedderUrl: EMBEDDER_URL, error: String(err?.message || err) }
    });
  }
});

// POST /embed - validates input then proxies to embedder
const EmbedReq = z.object({ text: z.string().min(1).max(20000) });
app.post("/embed", async (req: Request, res: Response) => {
  const parse = EmbedReq.safeParse(req.body);
  if (!parse.success) return res.status(400).json({ error: "invalid request body" });

  try {
    const payload = JSON.stringify(parse.data);
    const out = await fetchJSON(`${EMBEDDER_URL}/embed`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: payload
    });
    return res.json(out);
  } catch (err: any) {
    return res.status(502).json({ error: "embedder error", detail: String(err?.message || err) });
  }
});

// Start
app.listen(PORT, () => {
  console.log(`[coordinator] listening on http://127.0.0.1:${PORT}`);
  console.log(`[coordinator] EMBEDDER_URL = ${EMBEDDER_URL}`);
});
