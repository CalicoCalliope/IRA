// src/services/rankingService.ts
import axios from "axios";
import { RankRequest, RankResponse } from "../types.js";

const RANKER_SERVICE_URL = process.env.RANKER_SERVICE_URL || "http://localhost:5004";

/**
 * Call the Ranker service to re-rank candidate PEMs
 * @param req RankRequest prepared by the coordinator
 * @returns RankResponse containing best and alternate items
 */
export async function rankPEM(req: RankRequest): Promise<RankResponse> {
  try {
    const response = await axios.post(`${RANKER_SERVICE_URL}/rank`, req);
    return response.data as RankResponse;
  } catch (err: any) {
    if (err.response) {
      console.error("Ranker service error:", err.response.status, err.response.data);
    } else {
      console.error("Ranker service error:", err.message);
    }
    throw new Error("Failed to rank PEM candidates");
  }
}

// Optional: health check
export async function health(): Promise<any> {
  const response = await axios.get(`${RANKER_SERVICE_URL}/health`);
  return response.data;
}