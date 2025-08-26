import axios from "axios";
import { randomUUID } from "crypto";

const BASE_URL = "http://localhost:4000";

async function runTests() {
  console.log("=== DB Service Test ===");

  try {
    const id = randomUUID();

    // 1. Insert a PEM log
    const pemResp = await axios.post(`${BASE_URL}/pems`, {
      id,
      timestamp: new Date().toISOString(),
      pem: "Test error message",
      pemType: "TypeError",
      pemSkeleton: "Test skeleton",
      username: "tester",
      activeFile: "testFile.py",
      workingDirectory: "/tmp",
      directoryTree: ["file1.py", "file2.py"],
      isFirstOccurrence: true,
      llm: {
        hint: "Test hint",
        reasoning: "Test reasoning",
        answer: "Test answer",
      },
      pythonVersion: "3.11.5",
      packages: [{ name: "numpy", version: "1.25.0" }],
    });
    console.log("[POST /pems] Response:", pemResp.data);

    // 2. Fetch the PEM back
    const getPemResp = await axios.get(`${BASE_URL}/pems/${id}`);
    console.log("[GET /pems/:id] Response:", getPemResp.data);

    // 3. Insert embedding
    const embResp = await axios.post(`${BASE_URL}/embeddings`, {
      id,
      vector: Array(512).fill(0.5),
      timestamp: new Date().toISOString(),
      username: "tester",
      pemType: "TypeError",
    });
    console.log("[POST /embeddings] Response:", embResp.data);

    // 4. Retrieve embedding
    const getEmbResp = await axios.get(`${BASE_URL}/embeddings/${id}`);
    console.log("[GET /embeddings/:id] Response:", getEmbResp.data);

    console.log("✅ All DB service tests passed!");
  } catch (err: any) {
    console.error("❌ DB service test failed:", err.response?.data || err.message);
  }
}

runTests();