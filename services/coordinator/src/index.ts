// src/index.ts
import express from "express";
import dotenv from "dotenv";
import path from "path";
import pemRoutes from "./routes/pemRoutes.js";

// Load environment variables from .env
const envPath = path.resolve(__dirname, "../.env");
dotenv.config({ path: envPath });

const app = express();
const PORT = process.env.COORDINATOR_PORT || 5000;

// Middleware
app.use(express.json());

// Routes
app.use("/api/pems", pemRoutes);

// Health check
app.get("/health", (_req, res) => {
  res.json({ status: "up" });
});

// Start server
app.listen(PORT, () => {
  console.log(`[Coordinator] Running on http://localhost:${PORT}`);
});