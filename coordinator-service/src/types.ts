export interface PemLogEntry {
  id: string;
  timestamp: string;
  pem: string;
  pemType: string;
  pemSkeleton: string;
  code: string;
  username: string;
  activeFile: string;
  workingDirectory: string;
  directoryTree: string[];
  pythonVersion?: string;
  packages?: any[];
  isFirstOccurrence: boolean;
  llm: {
    hint?: string;
    reasoning?: string;
    answer?: string;
  };
}

export interface EmbeddingPoint {
  id: string;
  vector: number[];
  payload: {
    timestamp: string;
    username: string;
    pemType: string;
  };
}

// Ranking Params
export interface RankParams {
  k: number;                          // 1–10
  mmr_lambda: number;                  // 0–1
  confidence_floor: number;            // 0–1
  recency_half_life_days: number;      // >0
  skeleton_filter_threshold: number;   // 0–1
  allow_repeat_depth: number;          // 0–3
  allow_repeat_min_hours: number;      // >=0
  success_bonus_alpha: number;         // 0–0.2
}

// Context about the current PEM
export interface QueryContext {
  student_id: string;
  pemType: string;
  pemSkeleton: string;
  timestamp: string
  activeFile_hash: string;
  workingDirectory_hash: string;
  directoryTree: string[];
  packages: string[];
  pythonVersion: string;
  resolutionDepth?: number;            // 0–3
  current_pem_point_id?: string;
  code_slice?: string;
}

// Candidate prepared by Coordinator
export interface Candidate {
  id: string;
  vector_similarity: number;           // 0–1
  pemSkeleton: string;
  timestamp: string;                   // ISO datetime
  activeFile_hash: string;
  workingDirectory_hash: string;
  directoryTree: string[];
  packages: string[];
  pythonVersion: string;
  resolutionDepth?: number;            // 0–3
  activeFile_ext?: string;             // e.g. ".py"
}

// Request payload to /rank
export interface RankRequest {
  params: RankParams;
  query: QueryContext;
  candidates: Candidate[];
}

// Ranked item result
export interface RankedItem {
  id: string;
  score: number;                       // 0–1
  features: {
    skeleton: number;
    vector: number;
    recency: number;
    project: number;
    file: number;
    packages: number;
    pyver: number;
  };
  reasons: string[];
}

// Ranker response
export interface RankResponse {
  abstain: boolean;
  reason?: string;
  best?: RankedItem;
  alternates: RankedItem[];
}
