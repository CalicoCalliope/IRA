// src/services/dbService.ts
import axios from "axios";
import { PemLogEntry, PemSubmission, LLMResponse, UserEvent } from "../types.js";

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

interface DBEventCreateResponse {
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

export async function getPEMbyType(filters: {
  username?: string;
  pemType?: string;
}): Promise<PemLogEntry[]> {
  const params: Record<string, string> = {};
  if (filters.username) params.username = filters.username;
  if (filters.pemType) params.pemType = filters.pemType;

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
  pem: PemSubmission & { id:string, isFirstOccurrence: boolean; llm: LLMResponse; accessed: any }
): Promise<PemLogEntry> {
  const payload = { ...pem };
  await axios.post(`${DB_SERVICE_URL}/pems`, payload); // DB just stores what we send
  return payload as PemLogEntry
}

// -------------------------
// Update PEM fields
// -------------------------
export async function updatePEM(id: string, updates: Partial<PemLogEntry>): Promise<void> {
  await axios.patch<DBPatchResponse>(`${DB_SERVICE_URL}/pems/${id}`, updates);
}

// -------------------------
// Create User Event
// -------------------------
export async function createUserEvent(event: UserEvent): Promise<void> {
  await axios.post<DBEventCreateResponse>(`${DB_SERVICE_URL}/events`, event);
}
