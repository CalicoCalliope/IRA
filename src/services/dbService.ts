import axios from "axios";
import { PemLogEntry, EmbeddingPoint } from "../types";

const DB_SERVICE_URL = process.env.DB_SERVICE_URL || "http://localhost:4000";


/**
 * =====================
 * PEM Metadata (MongoDB)
 * =====================
 */

export async function savePemLog(entry: PemLogEntry) {
  const res = await axios.post(`${DB_SERVICE_URL}/pems`, entry);
  return res.data;
}

export async function getPemLog(id: string) {
  const res = await axios.get(`${DB_SERVICE_URL}/pems/${id}`);
  return res.data;
}

export async function getPemsByUser(username: string) {
  return (await axios.get(`${DB_SERVICE_URL}/pems`, { params: { username } })).data;
}

export async function getPemsByType(pemType: string) {
  return (await axios.get(`${DB_SERVICE_URL}/pems`, { params: { pemType } })).data;
}

export async function getPemsByUserAndType(pemType: string, username: string) {
  return (await axios.get(`${DB_SERVICE_URL}/pems`, { params: { username, pemType } })).data;
}

export async function updatePemLog(id: string, updates: Partial<PemLogEntry>) {
  return (await axios.patch(`${DB_SERVICE_URL}/pems/${id}`, updates)).data;
}

export async function deletePemLog(id: string) {
  return (await axios.delete(`${DB_SERVICE_URL}/pems/${id}`)).data;
}

/**
 * =====================
 * Embeddings (Qdrant)
 * =====================
 */
export async function saveEmbedding(entry: EmbeddingPoint) {
  return (await axios.post(`${DB_SERVICE_URL}/embeddings`, entry)).data;
}

export async function getEmbedding(pemId: string) {
  return (await axios.get(`${DB_SERVICE_URL}/embeddings/${pemId}`)).data;
}
  
/**
 * =====================
 * Healthcheck / Utility
 * =====================
 */
export async function pingDb() {
  return (await axios.get(`${DB_SERVICE_URL}/health`)).data;
}