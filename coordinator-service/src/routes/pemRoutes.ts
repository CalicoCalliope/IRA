// coordinator/src/routes/pemRoutes.ts
import { Router } from "express";
import dbService from "../services/dbService";
// import embedderService from "../services/embedderService";
import { PemLogEntry } from "../types";

const router = Router();

/**
 * Handle new PEM from the extension
 * - Generate UID
 * - Save to DB
 * - Send to embedder
 */
router.post("/handlePEM", async (req, res) => {
  try {
    const { pem, metadata } = req.body;

    if (!pem || !metadata) {
      return res.status(400).json({ error: "pem and metadata are required" });
    }

    // 1️⃣ Generate a UID for this PEM
    const pemId = crypto.randomUUID();

    // 2️⃣ Save PEM + metadata to Mongo via dbService
    const pemEntry: PemLogEntry = { id: pemId, ...metadata, pem };
    await dbService.savePemLog(pemEntry);

    // 3️⃣ Send PEM + UID to embedder service (placeholder for now)
    // await embedderService.embedAndStore({ id: pemId, pem, metadata });

    res.json({ status: "ok", id: pemId });
  } catch (err: any) {
    console.error("[Coordinator /handlePEM] Error:", err);
    res.status(500).json({ error: err.message });
  }
});

/**
 * Optional: Get PEM by ID
 */
router.get("/:id", async (req, res) => {
  try {
    const pem = await dbService.getPemLog(req.params.id);
    res.json({ status: "ok", data: pem });
  } catch (err: any) {
    console.error("[Coordinator GET /pems/:id] Error:", err);
    res.status(500).json({ error: err.message });
  }
});

/**
 * Optional: List PEMs with filters
 */
router.get("/", async (req, res) => {
  try {
    const filters = {
      username: req.query.username as string | undefined,
      pemType: req.query.pemType as string | undefined,
    };
    const pems = await dbService.getPemsByFilter(filters);
    res.json({ status: "ok", data: pems });
  } catch (err: any) {
    console.error("[Coordinator GET /pems] Error:", err);
    res.status(500).json({ error: err.message });
  }
});

export default router;