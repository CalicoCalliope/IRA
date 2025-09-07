// src/services/llmService.ts
import axios from "axios";
import { LLMRequest, LLMResponse } from "../types.js";

const LLM_SERVICE_URL = process.env.LLM_SERVICE_URL || "http://localhost:5004";

/**
 * Generate HRA (Hint / Reasoning / Answer) for a given PEM
 * @param req LLMRequest containing PEM info and context
 * @returns LLMResponse with hint, reasoning, answer
 */
export async function generateHRA(req: LLMRequest): Promise<LLMResponse> {
  try {
    const response = await axios.post(`${LLM_SERVICE_URL}/generate-hra`, req);
    return response.data as LLMResponse;
  } catch (err: any) {
    console.error("LLM service error:", err.message);
    throw new Error("Failed to generate HRA from LLM");
  }
}

// Optional: health check
export async function health(): Promise<any> {
  const response = await axios.get(`${LLM_SERVICE_URL}/health`);
  return response.data;
}