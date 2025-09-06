import axios from "axios";
import { PemLogEntry } from "../types.js";

const DB_SERVICE_URL = process.env.DB_SERVICE_URL || "http://localhost:4000";

interface SavePemResponse {
  status: string;
  id: string;
}

interface GetPemResponse {
  status: string;
  data: PemLogEntry;
}

interface GetPemsResponse {
  status: string;
  data: PemLogEntry[];
}

interface GenericStatusResponse {
  status: string;
}

const dbService = {
  async savePemLog(entry: PemLogEntry): Promise<SavePemResponse> {
    const res = await axios.post<SavePemResponse>(`${DB_SERVICE_URL}/pems`, entry);
    return res.data;
  },

  async getPemLog(id: string): Promise<PemLogEntry> {
    const res = await axios.get<GetPemResponse>(`${DB_SERVICE_URL}/pems/${id}`);
    return res.data.data;
  },

  async getPemsByFilter(filters: { username?: string; pemType?: string } = {}): Promise<PemLogEntry[]> {
    const res = await axios.get<GetPemsResponse>(`${DB_SERVICE_URL}/pems`, { params: filters });
    return res.data.data;
  },

  async updatePemLog(id: string, updates: Partial<PemLogEntry>): Promise<GenericStatusResponse> {
    const res = await axios.patch<GenericStatusResponse>(`${DB_SERVICE_URL}/pems/${id}`, updates);
    return res.data;
  },

  async deletePemLog(id: string): Promise<GenericStatusResponse> {
    const res = await axios.delete<GenericStatusResponse>(`${DB_SERVICE_URL}/pems/${id}`);
    return res.data;
  },

  async pingDb(): Promise<GenericStatusResponse> {
    const res = await axios.get<GenericStatusResponse>(`${DB_SERVICE_URL}/health`);
    return res.data;
  },
};

export default dbService;