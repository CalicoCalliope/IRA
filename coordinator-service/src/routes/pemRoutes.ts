import { Router } from "express";
import { savePemLog } from "../services/dbService";
import { getEmbedding } from "../services/embedderService";
import { getSimilarPEMs } from "../services/rankingService";
import { PemLogEntry } from "../types";

const router = Router();

router.post("/log", async (req, res) => {
  try {
    const entry: PemLogEntry = req.body;

    // Call embedder to enrich entry with embeddings
    const embedding = await getEmbedding(entry.pem);
    console.log("[Coordinator] Got embedding length:", embedding.length);

    // Save entry in DB (metadata + embedding separately)
    const saved = await savePemLog({ ...entry });
    res.json({ success: true, saved });
  } catch (err: any) {
    console.error("[Coordinator Error]", err.message);
    res.status(500).json({ error: "Failed to log PEM" });
  }
});

router.get("/similar/:id", async (req, res) => {
  try {
    const pemId = req.params.id;
    const results = await getSimilarPEMs(pemId);
    res.json(results);
  } catch (err: any) {
    console.error("[Coordinator Error]", err.message);
    res.status(500).json({ error: "Failed to fetch similar PEMs" });
  }
});

export default router;