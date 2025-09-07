// src/types.ts

// -------------------------
// PEM submission from frontend
// -------------------------
export interface PemSubmission {
  pem: string;                  // full error message
  pemType: string;
  pemSkeleton: string;
  code: string;                 // code snippet
  username: string;
  timestamp: string;            // ISO string
  activeFile: string;
  workingDirectory: string;
  directoryTree: string[];
  pythonVersion?: string;
  packages?: string[];
}

// -------------------------
// HRA (hint, reasoning, answer)
// -------------------------
export interface HRA {
  hint?: string;
  reasoning?: string;
  answer?: string;
}

// -------------------------
// PEM record in MongoDB
// -------------------------
export interface PemLogEntry extends PemSubmission {
  id: string;                   // unique ID (used in MongoDB & Milvus)
  isFirstOccurrence: boolean;
  llm: HRA;
  accessed: {
    hint?: boolean;
    reasoning?: boolean;
    answer?: boolean;
  };
}

// -------------------------
// Embedder request/response types
// -------------------------
export interface EmbedRequest {
  text: string;
  primary_key: string;           // PEM ID
  username: string;
  pem_type: string;
  timestamp: number;             // seconds since epoch
}

export interface EmbedResponse {
  vector: number[];
  dim: number;
  primary_key: string;
  timestamp: number;
}

export interface FilterResponseItem {
  primary_key: string;
  embedding: number[];
  timestamp: number;
  username: string;
  pem_type: string;
}

export interface FilterResponse {
  embeddings: FilterResponseItem[];
}

// -------------------------
// Ranker types
// -------------------------
export interface RankerCandidate {
  id: string;                    // PEM record ID
  vector_similarity: number;      // cosine similarity with current PEM
  pemSkeleton: string;
  timestamp: string;              // ISO string
  activeFile_hash: string;
  workingDirectory_hash: string;
  directoryTree: string[];
  packages: string[];
  pythonVersion?: string;
  resolutionDepth?: number;
}

export interface RankParams {
  k?: number;
  mmr_lambda?: number;
  confidence_floor?: number;
  recency_half_life_days?: number;
  skeleton_filter_threshold?: number;
  allow_repeat_depth?: number;
  allow_repeat_min_hours?: number;
  success_bonus_alpha?: number;
}

export interface QueryContext {
  student_id: string;
  pemType: string;
  pemSkeleton: string;
  timestamp: string;
  activeFile_hash: string;
  workingDirectory_hash: string;
  directoryTree: string[];
  packages: string[];
  pythonVersion?: string;
  resolutionDepth?: number;
  current_pem_point_id?: string;
  code_slice?: string;
}

export interface RankRequest {
  params: RankParams;
  query: QueryContext;
  candidates: RankerCandidate[];
}

export interface RankedItem {
  id: string;
  score: number;
  features: Record<string, number>;
  reasons: string[];
}

export interface RankResponse {
  abstain: boolean;
  reason?: string;
  best?: RankedItem;
  alternates: RankedItem[];
}

// -------------------------
// LLM service request/response
// -------------------------
export interface LLMRequest {
  pem: string;
  pemType: string;
  pemSkeleton: string;
  code: string;
  username: string;
  timestamp: string;
  activeFile: string;
  workingDirectory: string;
  directoryTree: string[];
  pythonVersion?: string;
  packages?: string[];
}

export interface LLMResponse {
  hint?: string;
  reasoning?: string;
  answer?: string;
}