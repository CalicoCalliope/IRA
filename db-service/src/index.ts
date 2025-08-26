import express from "express";
import * as dotenv from "dotenv";
import * as path from "path";
import { MongoClient } from "mongodb";
import { QdrantClient } from "@qdrant/js-client-rest";
import crypto from "crypto";

// Load .env using absolute path
const envPath = path.resolve(__dirname, "../.env");
dotenv.config({ path: envPath });
const PORT = process.env.PORT || 4000;

// --- MongoDB Setup ---
const MONGODB_URI = process.env.MONGODB_URI;
if (!MONGODB_URI) throw new Error("MONGODB_URI not defined in .env");

const mongo = new MongoClient(MONGODB_URI);
let pemCollection: any;

async function connectMongo() {
  await mongo.connect();
  console.log("[MongoDB] Connected successfully");
  const db = mongo.db("iraLogs");
  pemCollection = db.collection("pems");
}

// --- Qdrant Setup ---
const QDRANT_URL = process.env.QDRANT_URL!;
const QDRANT_KEY = process.env.QDRANT_KEY!;

if (!QDRANT_URL || !QDRANT_KEY) {
  throw new Error("QDRANT_URL or QDRANT_KEY not defined in .env");
}

const qdrant = new QdrantClient({
  url: QDRANT_URL,
  apiKey: QDRANT_KEY,
});

// --- Express App ---
const app = express();
app.use(express.json());

// --- PEM Routes ---
app.post("/pems", async (req, res) => {
  const entry = req.body;
  try {
    const result = await pemCollection.insertOne(entry);
    res.json({ status: "ok", id: entry.id || result.insertedId });
  } catch (err: any) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

app.get("/pems/:id", async (req, res) => {
  try {
    const pem = await pemCollection.findOne({ id: req.params.id });
    res.json(pem);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// --- Embedding Routes ---
app.post("/embeddings", async (req, res) => {
  try {
    const { id, vector, timestamp, username, pemType } = req.body;

    // Validate vector length
    if (!vector || !Array.isArray(vector) || vector.length !== 512) {
      return res
        .status(400)
        .json({ error: "vector (512-dim number[]) is required" });
    }

    const point = {
      id: id || crypto.randomUUID(),
      vector,
      payload: {
        timestamp: timestamp || new Date().toISOString(),
        username: username || "unknown",
        pemType: pemType || "UnknownError",
      },
    };

    const result = await qdrant.upsert("pems_embeddings", { points: [point] });
    console.log("[Upsert] Result:", result);

    res.json({ status: "ok", id: point.id });
  } catch (err: any) {
    console.error("[POST /embeddings] Error:", err.response?.data || err.message);
    res.status(500).json({ error: err.message });
  }
});

app.get("/embeddings/:id", async (req, res) => {
  try {
    const result = await qdrant.retrieve("pems_embeddings", { ids: [req.params.id] });
    res.json(result);
  } catch (err: any) {
    console.error("[GET /embeddings/:id] Error:", err.response?.data || err.message);
    res.status(500).json({ error: err.message });
  }
});

// --- Health Check ---
app.get("/health", (_req, res) => res.json({ status: "up" }));

// --- Start Server ---
(async () => {
  try {
    await connectMongo();

    // Ensure Qdrant collection exists
    const collections = await qdrant.getCollections();
    const names = collections.collections.map((c) => c.name);
    console.log("[Qdrant] Existing collections:", names);

    if (!names.includes("pems_embeddings")) {
      console.log("[Qdrant] Creating collection 'pems_embeddings'...");
      await qdrant.createCollection("pems_embeddings", {
        vectors: {
          size: 512,
          distance: "Cosine",
        },
      });
      console.log("[Qdrant] Collection 'pems_embeddings' created.");
    }

    app.listen(PORT, () =>
      console.log(`[DB Service] Running on http://localhost:${PORT}`)
    );
  } catch (err) {
    console.error("[DB Service Startup Error]", err);
    process.exit(1);
  }
})();