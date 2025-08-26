import axios from "axios";

const RANKER_URL = process.env.RANKER_URL || "http://localhost:6000";

export async function getSimilarPEMs(pemId: string) {
  const res = await axios.get(`${RANKER_URL}/rank?pemId=${pemId}`);
  return res.data; // expected to return [{pemId, score}, ...]
}