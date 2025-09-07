// src/services/dbService.ts
import axios from "axios";
import { PemLogEntry, PemSubmission, HRA } from "../types.js";

// Use environment variable for DB service URL
const DB_SERVICE_URL = process.env.DB_SERVICE_URL || "http://localhost:5001";

// -------------------------
// Response interfaces
// -------------------------
interface DBListResponse {
  status: string;
  data: PemLogEntry[];
}

interface DBGetResponse {
  status: string;
  data: PemLogEntry;
}

interface DBCreateResponse {
  status: string;
  id: string;
}

interface DBPatchResponse {
  status: string;
}

// -------------------------
// Fetch PEMs by filters
// -------------------------
export async function getPEMs(filters: {
  username?: string;
  pemType?: string;
  pemSkeleton?: string;
}): Promise<PemLogEntry[]> {
  const params: Record<string, string> = {};
  if (filters.username) params.username = filters.username;
  if (filters.pemType) params.pemType = filters.pemType;
  if (filters.pemSkeleton) params.pemSkeleton = filters.pemSkeleton;

  const response = await axios.get<DBListResponse>(`${DB_SERVICE_URL}/pems`, { params });
  return response.data.data || [];
}

// -------------------------
// Fetch PEM by ID
// -------------------------
export async function getPEMById(id: string): Promise<PemLogEntry> {
  const response = await axios.get<DBGetResponse>(`${DB_SERVICE_URL}/pems/${id}`);
  return response.data.data;
}

// -------------------------
// Create new PEM
// -------------------------
export async function createPEM(
  pem: PemSubmission & { isFirstOccurrence: boolean; llm: HRA; accessed: any }
): Promise<PemLogEntry> {
  const payload = { ...pem };
  const response = await axios.post<DBCreateResponse>(`${DB_SERVICE_URL}/pems`, payload);
  return {
    ...payload,
    id: response.data.id,
  } as PemLogEntry;
}

// -------------------------
// Update PEM fields
// -------------------------
export async function updatePEM(id: string, updates: Partial<PemLogEntry>): Promise<void> {
  await axios.patch<DBPatchResponse>(`${DB_SERVICE_URL}/pems/${id}`, updates);
}