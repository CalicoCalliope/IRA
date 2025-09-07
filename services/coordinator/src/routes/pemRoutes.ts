// src/routes/pemRoutes.ts
import express, { Request, Response } from "express";
import { PemSubmission, PemLogEntry, EmbedRequest, EmbedResponse, LLMRequest, LLMResponse, RankRequest, RankResponse, RankerCandidate } from "../types.js";
import * as dbService from "../services/dbService.js";
import * as embedderService from "../services/embedderService.js";
import * as llmService from "../services/llmService.js";
import * as rankingService from "../services/rankingService.js";
import crypto from "crypto";

const router = express.Router();

/**
 * Simple SHA256 hash utility for strings
 */
function hashString(input: string): string {
  return crypto.createHash("sha256").update(input).digest("hex");
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
  try {
    const pemSubmission: PemSubmission = req.body;

    // Step 1: Check if PEM is first occurrence
    const existingPEMs = await dbService.getPEMs({
      username: pemSubmission.username,
      pemType: pemSubmission.pemType,
      pemSkeleton: pemSubmission.pemSkeleton,
    });

    const isFirstOccurrence = existingPEMs.length === 0;
    let pemRecord: PemLogEntry;

    if (isFirstOccurrence) {
      // ---------------------
      // FIRST OCCURRENCE WORKFLOW
      // ---------------------
      pemRecord = await dbService.createPEM({
        ...pemSubmission,
        isFirstOccurrence: true,
        llm: {},
        accessed: {},
      });

      // Embed the code snippet
      const embedRequest: EmbedRequest = {
        text: pemSubmission.code,
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
        code: pemSubmission.code,
        activeFile: pemSubmission.activeFile,
      };

      const llmResponse: LLMResponse = await llmService.generateHRA(llmRequest);

      // Update MongoDB record with HRA
      await dbService.updatePEM(pemRecord.id, { llm: llmResponse });

      // Return HRA to frontend
      return res.json({ isFirstOccurrence: true, hra: llmResponse });
    } else {
      // ---------------------
      // REPEATED PEM WORKFLOW
      // ---------------------
      pemRecord = existingPEMs[0]; // Take first existing record (customizable)

      // Fetch candidate embeddings from Embedder
      const filterResponse = await embedderService.filterEmbeddings({
        username: pemSubmission.username,
        pem_type: pemSubmission.pemType,
        n_results: 100,
      });

      // Prepare Ranker candidates
      const candidates: RankerCandidate[] = filterResponse.embeddings.map((e) => ({
        id: e.primary_key,
        vector_similarity: 0, // Ranker computes actual similarity
        pemSkeleton: pemSubmission.pemSkeleton,
        timestamp: new Date(e.timestamp * 1000).toISOString(),
        activeFile_hash: hashString(pemSubmission.activeFile),
        workingDirectory_hash: hashString(pemSubmission.workingDirectory),
        directoryTree: pemSubmission.directoryTree,
        packages: pemSubmission.packages || [],
        pythonVersion: pemSubmission.pythonVersion,
      }));

      // Prepare RankRequest
      const rankRequest: RankRequest = {
        params: {}, // Optional: customize RankParams
        query: {
          student_id: pemSubmission.username,
          pemType: pemSubmission.pemType,
          pemSkeleton: pemSubmission.pemSkeleton,
          timestamp: pemSubmission.timestamp,
          activeFile_hash: hashString(pemSubmission.activeFile),
          workingDirectory_hash: hashString(pemSubmission.workingDirectory),
          directoryTree: pemSubmission.directoryTree,
          packages: pemSubmission.packages || [],
          pythonVersion: pemSubmission.pythonVersion,
        },
        candidates,
      };

      // Call Ranker
      const rankResponse: RankResponse = await rankingService.rankPEM(rankRequest);

      // Fetch HRA for best-ranked PEM
      let hra: LLMResponse = {};
      if (rankResponse.best?.id) {
        const bestPEM = await dbService.getPEMById(rankResponse.best.id);
        hra = bestPEM.llm;
      }

      // Return HRA to frontend
      return res.json({ isFirstOccurrence: false, hra });
    }
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
    const accessedUpdate = req.body as { hint?: boolean; reasoning?: boolean; answer?: boolean };

    if (!accessedUpdate || Object.keys(accessedUpdate).length === 0) {
      return res.status(400).json({ error: "No accessed fields provided" });
    }

    // Fetch existing PEM
    const pem = await dbService.getPEMById(pemId);
    if (!pem) return res.status(404).json({ error: "PEM not found" });

    // Merge existing accessed fields with updates
    const updatedAccessed = { ...pem.accessed, ...accessedUpdate };

    // Update in DB
    await dbService.updatePEM(pemId, { accessed: updatedAccessed });

    return res.json({ status: "ok", accessed: updatedAccessed });
  } catch (err: any) {
    console.error("Error updating accessed HRA:", err);
    return res.status(500).json({ error: err.message });
  }
});


export default router;