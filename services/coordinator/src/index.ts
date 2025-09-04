import "dotenv/config";
import express, { Request, Response } from "express";
import { z } from "zod";

const PORT = Number(process.env.PORT || 8000);
const EMBEDDER_URL = process.env.EMBEDDER_URL || "http://127.0.0.1:8001";

async function withTimeout<T>(p: Promise<T>, ms = 10000): Promise<T> {
  const t = new Promise<never>((_, rej) => setTimeout(() => rej(new Error("timeout")), ms));
  return Promise.race([p, t]);
}
async function fetchJSON(url: string, init?: RequestInit) {
  const res = await withTimeout(fetch(url, init));
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
  return res.json();
}

const app = express();
app.use(express.json({ limit: "512kb" }));

app.get("/health", async (_req: Request, res: Response) => {
  try {
    const health = await fetchJSON(`${EMBEDDER_URL}/health`);
    res.json({ coordinator: { ok: true, embedderUrl: EMBEDDER_URL }, embedder: health });
  } catch (e: any) {
    res.status(503).json({ coordinator: { ok: false, embedderUrl: EMBEDDER_URL, error: String(e?.message || e) } });
  }
});

const EmbedReq = z.object({ text: z.string().min(1).max(20000) });
app.post("/embed", async (req: Request, res: Response) => {
  const parsed = EmbedReq.safeParse(req.body);
  if (!parsed.success) return res.status(400).json({ error: "invalid request body" });
  try {
    const out = await fetchJSON(`${EMBEDDER_URL}/embed`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(parsed.data)
    });
    res.json(out);
  } catch (e: any) {
    res.status(502).json({ error: "embedder error", detail: String(e?.message || e) });
  }
});

app.listen(PORT, () => {
  console.log(`[coordinator] listening on http://127.0.0.1:${PORT}`);
  console.log(`[coordinator] EMBEDDER_URL = ${EMBEDDER_URL}`);
});
