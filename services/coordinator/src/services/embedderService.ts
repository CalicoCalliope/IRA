import axios from "axios";

const EMBEDDER_URL = process.env.EMBEDDER_URL || "http://localhost:5000";

export async function getEmbedding(text: string): Promise<number[]> {
  const res = await axios.post(`${EMBEDDER_URL}/embed`, { text });
  return res.data.embedding; // { embedding: [ ... ] }
}
