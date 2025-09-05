import express, { Request, Response } from "express";
import dotenv from "dotenv";
import crypto from "crypto";
import dbService from "./services/dbService";
// import { embedderService } from "./services/embedderService";
import pemRoutes from "./routes/pemRoutes";
import rankingRoutes from "./routes/rankingRoutes";
import { PemLogEntry } from "./types";
import { z } from "zod";

/* -----------------------------
 Load environment variables
 -----------------------------*/
dotenv.config();

const COOR_PORT = Number(process.env.COOR_PORT || 3000);
const EMBEDDER_URL = process.env.EMBEDDER_URL || "http://127.0.0.1:8001";

/* -----------------------------
  App and Routes
 -----------------------------*/

export const app = express();
app.use(express.json());
app.use("/pems", pemRoutes);
app.use("/ranking", rankingRoutes);
// TODO: add routes for embedder and llm services

/* -----------------------------
 Helper Functions
 -----------------------------*/
async function withTimeout<T>(p: Promise<T>, ms = 10000): Promise<T> {
  const t = new Promise<never>((_, rej) => setTimeout(() => rej(new Error("timeout")), ms));
  return Promise.race([p, t]);
}

async function fetchJSON(url: string, init?: RequestInit) {
  const res = await withTimeout(fetch(url, init));
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
  return res.json();
}

// Main entrypoint for PEMs
app.post("/handlePEM", async (req, res) => {
  try {
    const { pem, pemType, pemSkeleton, code, username, activeFile, workingDirectory, directoryTree, pythonVersion, packages } = req.body;

    if (!pem || typeof pem !== "string") {
      return res.status(400).json({ error: "PEM must be a string" });
    }

    const pemId = crypto.randomUUID();

    // Construct a full PemLogEntry object
    const entry: PemLogEntry = {
      id: pemId,
      timestamp: new Date().toISOString(),
      pem,
      pemType,
      pemSkeleton,
      code,
      username,
      activeFile,
      workingDirectory,
      directoryTree,
      pythonVersion,
      packages,
      isFirstOccurrence: false, // coordinator/db can set this after checking history
      llm: {},
    };

    // Save PEM metadata in Mongo
    await dbService.savePemLog(entry);

    // Send PEM to embedder service (it will generate + store vector in Qdrant)
    // await embedderService.embedAndStore(entry);

    res.json({ status: "ok", id: pemId });
  } catch (err: any) {
    console.error("[Coordinator] Error:", err);
    res.status(500).json({ error: err.message });
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


app.listen(COOR_PORT, () => {
  console.log(`[Coordinator Service] listening on port ${COOR_PORT}`);
});