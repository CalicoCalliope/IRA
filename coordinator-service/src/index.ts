import express from "express";
import dotenv from "dotenv";
import crypto from "crypto";
import dbService from "./services/dbService";
// import { embedderService } from "./services/embedderService";
import pemRoutes from "./routes/pemRoutes";
import { PemLogEntry } from "./types";

dotenv.config();

export const app = express();
app.use(express.json());

// Routes
app.use("/pems", pemRoutes);

// Main entrypoint for PEMs
app.post("/handlePEM", async (req, res) => {
  try {
    const { pem, pemType, pemSkeleton, code, username, activeFile, workingDirectory, directoryTree, pythonVersion, packages } = req.body;

    if (!pem || typeof pem !== "string") {
      return res.status(400).json({ error: "PEM must be a string" });
    }

    const pemId = crypto.randomUUID();

    // Construct a full PemLogEntry object
    const entry: PemLogEntry = {
      id: pemId,
      timestamp: new Date().toISOString(),
      pem,
      pemType,
      pemSkeleton,
      code,
      username,
      activeFile,
      workingDirectory,
      directoryTree,
      pythonVersion,
      packages,
      isFirstOccurrence: false, // coordinator/db can set this after checking history
      llm: {},
    };

    // Save PEM metadata in Mongo
    await dbService.savePemLog(entry);

    // Send PEM to embedder service (it will generate + store vector in Qdrant)
    // await embedderService.embedAndStore(entry);

    res.json({ status: "ok", id: pemId });
  } catch (err: any) {
    console.error("[Coordinator] Error:", err);
    res.status(500).json({ error: err.message });
  }
});

const PORT = process.env.COOR_PORT || 3000;
app.listen(PORT, () => {
  console.log(`[Coordinator Service] listening on port ${PORT}`);
});