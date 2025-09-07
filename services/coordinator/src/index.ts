// src/index.ts
import express from "express";
import dotenv from "dotenv";
import path from "path";
import { fileURLToPath } from "url";
import pemRoutes from "./routes/pemRoutes.js";

// Compute __dirname in ES module context
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables from .env
const envPath = path.resolve(__dirname, "../.env");
dotenv.config({ path: envPath });

const app = express();
const PORT = parseInt(process.env.COORDINATOR_PORT || "3000", 10);

// Middleware
app.use(express.json());

// Routes
app.use("/api/pems", pemRoutes);

// Health check
app.get("/health", (_req, res) => {
  res.json({ status: "up" });
});

// Start server
app.listen(PORT, "0.0.0.0", () =>
  console.log(`[Coordinator] Running on http://0.0.0.0:${PORT}`)
);