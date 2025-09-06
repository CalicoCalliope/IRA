import axios from "axios";
import { RankRequest, RankResponse } from "../types.js";

export class RankingService {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    // Either inject via constructor or use env var
    this.baseUrl = baseUrl || process.env.RANKING_URL || "http://localhost:8000";
  }

  async health(): Promise<boolean> {
    try {
      const res = await axios.get<{ ok: boolean }>(`${this.baseUrl}/health`);
      return res.data.ok === true;
    } catch (err) {
      return false;
    }
  }

  async rank(req: RankRequest): Promise<RankResponse> {
    try {
      const res = await axios.post<RankResponse>(`${this.baseUrl}/rank`, req);
      return res.data;
    } catch (err: any) {
      throw new Error(`Ranking service error: ${err.message}`);
    }
  }
}