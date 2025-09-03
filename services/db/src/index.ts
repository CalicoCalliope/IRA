import express from "express";
import * as dotenv from "dotenv";
import * as path from "path";
import { MongoClient } from "mongodb";
import { PemLogEntry } from "./types";

// Load .env using absolute path
const envPath = path.resolve(__dirname, "../.env");
dotenv.config({ path: envPath });

// --- MongoDB Setup ---
const MONGODB_URI = process.env.MONGODB_URI;
if (!MONGODB_URI) throw new Error("MONGODB_URI not defined in .env");

let mongo: MongoClient;
let pemCollection: any;

export async function connectMongo(testDbName?: string) {
  const MONGODB_URI = process.env.MONGODB_URI;
  if (!MONGODB_URI) throw new Error("MONGODB_URI not defined in .env");

  mongo = new MongoClient(MONGODB_URI);
  await mongo.connect();
  const dbName = testDbName || "iraLogs";
  const db = mongo.db(dbName);
  pemCollection = db.collection<PemLogEntry>("pems");
  console.log(`[MongoDB] Connected to ${dbName}`);
}

export function getPemCollection() {
  if (!pemCollection) throw new Error("MongoDB not connected yet");
  return pemCollection;
}

// --- Express App ---
export const app = express();
app.use(express.json());

// --- PEM Routes ---

// Create PEM
app.post("/pems", async (req, res) => {
  const entry: PemLogEntry = req.body;
  try {
    const result = await pemCollection.insertOne(entry);
    res.json({ status: "ok", id: entry.id || result.insertedId });
  } catch (err: any) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

// Get PEM by ID
app.get("/pems/:id", async (req, res) => {
  try {
    const pem = await pemCollection.findOne({ id: req.params.id });
    if (!pem) return res.status(404).json({ error: "PEM not found" });
    res.json({ status: "ok", data: pem });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Get PEMs with optional filters (username, pemType)
app.get("/pems", async (req, res) => {
  try {
    const query: Partial<PemLogEntry> = {};
    if (req.query.username) query.username = String(req.query.username);
    if (req.query.pemType) query.pemType = String(req.query.pemType);

    const results = await pemCollection.find(query).toArray();
    res.json({ status: "ok", data: results });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Update PEM
app.patch("/pems/:id", async (req, res) => {
  try {
    const updates: Partial<PemLogEntry> = req.body;
    const result = await pemCollection.updateOne({ id: req.params.id }, { $set: updates });
    if (result.matchedCount === 0) return res.status(404).json({ error: "PEM not found" });
    res.json({ status: "ok" });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Delete PEM
app.delete("/pems/:id", async (req, res) => {
  try {
    const result = await pemCollection.deleteOne({ id: req.params.id });
    if (result.deletedCount === 0) return res.status(404).json({ error: "PEM not found" });
    res.json({ status: "ok" });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Health Check
app.get("/health", (_req, res) => res.json({ status: "up" }));

// --- Start Server only if not in test environment ---
if (process.env.NODE_ENV !== "test") {
  const PORT = process.env.PORT || 4000;

  (async () => {
    try {
      await connectMongo();
      app.listen(PORT, () =>
        console.log(`[DB Service] Running on http://localhost:${PORT}`)
      );
    } catch (err) {
      console.error("[DB Service Startup Error]", err);
      process.exit(1);
    }
  })();
}