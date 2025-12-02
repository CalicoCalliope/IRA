// src/routes/pemRoutes.ts
import express, { Request, Response } from "express";
import { PemSubmission, PemLogEntry, EmbedRequest, EmbedResponse, LLMRequest, LLMResponse, RankRequest, RankResponse, RankerCandidate } from "../types.js";
import * as dbService from "../services/dbService.js";
import * as embedderService from "../services/embedderService.js";
import * as llmService from "../services/llmService.js";
import * as rankingService from "../services/rankingService.js";
import crypto from "crypto";
import {v4 as uuidv4} from 'uuid';
const router = express.Router();

/**
 * Simple SHA256 hash utility for strings
 */
function hashString(input: string): string {
  return crypto.createHash("sha256").update(input).digest("hex");
}

/**
 * Extracts the active task snippet from the full code.
 * Assumes one active task is active at a time.
 * Returns only uncommented lines from the first block that contains them.
 */
export function extractTaskSnippet(fullCode: string): string {
  return fullCode
    .split("\n")
    .map(line => {
      // Ignore shebangs (#!) but strip normal comments
      if (line.trim().startsWith("#!")) {
        return line; 
      }

      let inString = false;
      let stringChar = "";
      let result = "";

      for (let i = 0; i < line.length; i++) {
        const char = line[i];
        const prevChar = i > 0 ? line[i - 1] : "";

        // Detect string start
        if (!inString && (char === '"' || char === "'")) {
          inString = true;
          stringChar = char;
          result += char;
        }
        // Detect string end (ignore escaped quotes)
        else if (inString && char === stringChar && prevChar !== "\\") {
          inString = false;
          result += char;
        }
        // If we see # outside a string, cut the rest of the line
        else if (!inString && char === "#") {
          break;
        }
        else {
          result += char;
        }
      }

      return result.trimEnd(); // strip trailing spaces
    })
    .join("\n")
    .trim();
}

/** Normalize package list to lowercase names without versions
 */
function normalizePackages(pkgs?: any[]): string[] {
  if (!Array.isArray(pkgs)) return [];
  return pkgs
    .map(p => {
      if (typeof p === "string") return p.split("==")[0].toLowerCase();
      if (typeof p === "object" && p?.name) return String(p.name).toLowerCase();
      return "";
    })
    .filter(Boolean);
}

/**
 * POST /process-pem
 * Orchestrates the full PEM workflow:
 * 1. Check first occurrence in DB
 * 2. Save PEM record if first occurrence
 * 3. Embed code snippet
 * 4. Call LLM for HRA (if first occurrence)
 * 5. If repeated, call Embedder -> Ranker -> fetch previous HRA
 * 6. Return HRA to frontend
 */
router.post("/process-pem", async (req: Request, res: Response) => {

  const EXTENSION_MODE: "full" | "baseline" =
  req.body.mode === "full" ? "full" : "baseline"; // default to baseline
  console.log("[Coordinator] Extension mode from request:", EXTENSION_MODE);

  try {
    const pemSubmission: PemSubmission = req.body;

    let contextCode = extractTaskSnippet(pemSubmission.code);
    console.log("Extracted context code:\n", contextCode);

    // Check if PEM is first occurrence
    const existingPEMs = await dbService.getPEMs({
      username: pemSubmission.username,
      pemType: pemSubmission.pemType,
      pemSkeleton: pemSubmission.pemSkeleton,
    });

    const isFirstOccurrence = existingPEMs.length === 0;
    let pemRecord: PemLogEntry;
    let myuuid = uuidv4();

    pemRecord = await dbService.createPEM({
      id: myuuid,
      ...pemSubmission,
      isFirstOccurrence: isFirstOccurrence,
      llm: {},
      accessed: {},
      mode: EXTENSION_MODE,
    });

    // Embed the code snippet
    const embedRequest: EmbedRequest = {
      text: contextCode,
      primary_key: pemRecord.id,
      username: pemSubmission.username,
      pem_type: pemSubmission.pemType,
      timestamp: Math.floor(new Date(pemSubmission.timestamp).getTime() / 1000),
    };
    const embedResponse: EmbedResponse = await embedderService.createEmbedding(embedRequest);

    // Call LLM for HRA
    const llmRequest: LLMRequest = {
      pemType: pemSubmission.pemType,
      pem: pemSubmission.pem,
      code: contextCode,
      activeFile: pemSubmission.activeFile,
    };

    const llmResponse: LLMResponse = await llmService.generateHRA(llmRequest);

    // Update MongoDB record with HRA
    await dbService.updatePEM(pemRecord.id, { llm: llmResponse, code: contextCode });

    // Decide what to return based on experiment mode
    if (EXTENSION_MODE === "baseline") {
      // Show LLM output directly
      return res.json({ isFirstOccurrence, code: contextCode, hra: llmResponse });
    }

    if (EXTENSION_MODE === "full" && !isFirstOccurrence) {
      // Fetch candidate embeddings from Embedder
      const filterResponse = await embedderService.filterEmbeddings({
        username: pemSubmission.username,
        pem_type: pemSubmission.pemType,
        n_results: 100,
      });

      // Exclude the current PEM from the candidates (avoid self-match)
      const candidates = filterResponse.embeddings
        .filter(e => e.primary_key !== pemRecord.id)
        .map(e => ({
          id: e.primary_key,
          vector_similarity: 0, // Ranker computes actual similarity internally
          pemSkeleton: pemSubmission.pemSkeleton,
          timestamp: new Date(e.timestamp * 1000).toISOString(),
          activeFile_hash: hashString(pemSubmission.activeFile),
          workingDirectory_hash: hashString(pemSubmission.workingDirectory),
          directoryTree: pemSubmission.directoryTree || [],
          packages: normalizePackages(pemSubmission.packages),
          pythonVersion: pemSubmission.pythonVersion,
        }));

      // Prepare RankRequest
      const rankRequest: RankRequest = {
        params: {
          k: 3,
          mmr_lambda: 0.7,
          confidence_floor: 0.5,
          recency_half_life_days: 14.0,
          skeleton_filter_threshold: 0.6,
          allow_repeat_depth: 3,
          allow_repeat_min_hours: 24.0,
          success_bonus_alpha: 0.03,
        },
        query: {
          student_id: pemSubmission.username,
          pemType: pemSubmission.pemType,
          pemSkeleton: pemSubmission.pemSkeleton,
          timestamp: new Date(pemSubmission.timestamp).toISOString(),
          activeFile_hash: hashString(pemSubmission.activeFile),
          workingDirectory_hash: hashString(pemSubmission.workingDirectory),
          directoryTree: pemSubmission.directoryTree || [],
          packages: normalizePackages(pemSubmission.packages),
          pythonVersion: pemSubmission.pythonVersion,
        },
        candidates, // use filtered list
      };

      // Debug: see what ranker got
      console.log("[Coordinator] Sending candidates to ranker:", candidates.map(c => c.id));

      // Call Ranker
      const rankResponse: RankResponse = await rankingService.rankPEM(rankRequest);

      // Debug: see what coordinator received
      console.log("[Coordinator] Ranker response:", JSON.stringify(rankResponse, null, 2));

      // Fetch HRA for best-ranked PEM
      let hra: LLMResponse = {};
      if (rankResponse.best?.id) {
        const bestPEM = await dbService.getPEMById(rankResponse.best.id);
        hra = bestPEM.llm;
        contextCode = bestPEM.code;
      }

      // Return HRA to frontend
      return res.json({ isFirstOccurrence: isFirstOccurrence, code: contextCode, hra });
    }

    return res.json({ isFirstOccurrence: isFirstOccurrence, code: contextCode, hra: llmResponse });
  } catch (err: any) {
    console.error("Error processing PEM:", err);
    return res.status(500).json({ error: err.message });
  }
});

/**
 * PATCH /accessed/:pemId
 * Mark which parts of HRA the user has seen
 * Body: { hint?: boolean, reasoning?: boolean, answer?: boolean }
 */
router.patch("/accessed/:pemId", async (req: Request, res: Response) => {
  try {
    const pemId = req.params.pemId;
    const updates = req.body as { hint?: boolean; reasoning?: boolean; answer?: boolean };

    if (!updates || Object.keys(updates).length === 0) {
      return res.status(400).json({ error: "No accessed fields provided" });
    }

    // Fetch existing PEM
    const pem = await dbService.getPEMById(pemId);
    if (!pem) return res.status(404).json({ error: "PEM not found" });

    // Merge existing accessed fields with updates
    const updatedAccessed = { ...pem.accessed, ...updates };

    // Append timestamped HRA events
    const newEvents = Object.keys(updates)
      .filter(key => 
        updates[key as keyof typeof updates] === true &&
        !pem.accessed[key as keyof typeof pem.accessed] // <-- only if not previously accessed
      )
      .map(key => ({
        type: key as "hint" | "reasoning" | "answer",
        timestamp: new Date().toISOString()
      }));

    const updatedEvents = [...(pem.hraEvents || []), ...newEvents];

    // Update in DB
    await dbService.updatePEM(pemId, { accessed: updatedAccessed, hraEvents: updatedEvents });

    return res.json({ status: "ok", accessed: updatedAccessed, hraEvents: updatedEvents });
  } catch (err: any) {
    console.error("Error updating accessed HRA:", err);
    return res.status(500).json({ error: err.message });
  }
});

export default router;