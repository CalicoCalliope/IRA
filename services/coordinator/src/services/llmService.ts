// src/services/llmService.ts
import axios from "axios";
import { LLMRequest, LLMResponse } from "../types.js";

const LLM_SERVICE_URL = process.env.LLM_SERVICE_URL || "http://localhost:5003";
const IRA_SHARED_SECRET = process.env.IRA_SHARED_SECRET || "";
const IRA_TOKEN_HEADER = process.env.IRA_TOKEN_HEADER || "X-IRA-Token";

// GuidanceResponse shape from LLM service
interface GuidanceResponse {
  tier1: string;
  tier2: string;
  tier3: Record<string, any>;
  notes?: string;
}

/**
 * Generate HRA (Hint / Reasoning / Answer) for a given PEM
 * @param req LLMRequest containing PEM info and context
 * @returns LLMResponse with hint, reasoning, answer
 */
export async function generateHRA(req: LLMRequest): Promise<LLMResponse> {
  try {
    // Map coordinator LLMRequest to LLM service GuidanceRequest
    const guidanceRequest = {
      error_type: req.pemType,
      pem_text: req.pem,
      user_code: req.code,
      filename: req.activeFile,
    };

    const response = await axios.post<GuidanceResponse>(
      `${LLM_SERVICE_URL}/v1/guidance`,
      guidanceRequest,
      {
        headers: {
          [IRA_TOKEN_HEADER]: IRA_SHARED_SECRET,
        },
      }
    );

    const data = response.data;

    // Map LLM tiers to simplified LLMResponse
    const hra: LLMResponse = {
      hint: data.tier1 || "",
      reasoning: data.tier2 || "",
      answer: data.tier3 || "",
    };

    return hra;
  } catch (err: any) {
    console.error(
      "LLM service error:",
      err.response?.status,
      err.response?.data || err.message
    );
    throw new Error("Failed to generate HRA from LLM");
  }
}

// Optional: health check
export async function health(): Promise<any> {
  const response = await axios.get(`${LLM_SERVICE_URL}/health`, {
    headers: {
      [IRA_TOKEN_HEADER]: IRA_SHARED_SECRET,
    },
  });
  return response.data;
}