// src/services/embedderService.ts
import axios from "axios";
import { EmbedRequest, EmbedResponse, FilterResponse, FilterResponseItem } from "../types.js";

const EMBEDDER_SERVICE_URL = process.env.EMBEDDER_SERVICE_URL || "http://localhost:5002";

// -------------------------
// Create embedding for a code snippet
// -------------------------
export async function createEmbedding(req: EmbedRequest): Promise<EmbedResponse> {
  const response = await axios.post(`${EMBEDDER_SERVICE_URL}/embed`, req);
  return response.data as EmbedResponse;
}

// -------------------------
// Filter embeddings by username and PEM type
// -------------------------
export async function filterEmbeddings(params: {
  username?: string;
  pem_type?: string;
  n_results?: number;
}): Promise<FilterResponse> {
  const query: any = {};
  if (params.username) query.username = params.username;
  if (params.pem_type) query.pem_type = params.pem_type;
  query.n_results = params.n_results || 100;

  const response = await axios.get(`${EMBEDDER_SERVICE_URL}/filter`, { params: query });
  return response.data as FilterResponse;
}

// -------------------------
// Optional: health check
// -------------------------
export async function health(): Promise<any> {
  const response = await axios.get(`${EMBEDDER_SERVICE_URL}/health`);
  return response.data;
}