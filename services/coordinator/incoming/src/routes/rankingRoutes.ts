import express from "express";
import { RankingService } from "../services/rankingService";
import { RankRequest } from "../types";

const router = express.Router();
const rankingService = new RankingService();

// Health proxy → check if FastAPI service is alive
router.get("/health", async (req, res) => {
  try {
    const ok = await rankingService.health();
    res.json({ ok });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Ranking proxy → forward RankRequest to FastAPI ranker
router.post("/rank", async (req, res) => {
  try {
    const body = req.body as RankRequest;
    const result = await rankingService.rank(body);
    res.json(result);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

export default router;