import { RankingService } from "../src/services/rankingService";
import { RankRequest } from "../src/types";

describe("Coordinator → Ranking Service integration", () => {
  let rankingService: RankingService;
  let testRequest: RankRequest;

  beforeAll(() => {
    rankingService = new RankingService(); // uses RANKING_URL or localhost:8000

    testRequest = {
      params: {
        k: 2,
        mmr_lambda: 0.7,
        confidence_floor: 0.1,
        recency_half_life_days: 7,
        skeleton_filter_threshold: 0.5,
        allow_repeat_depth: 1,
        allow_repeat_min_hours: 1,
        success_bonus_alpha: 0.05,
      },
      query: {
        student_id: "user123",
        pemType: "TypeError",
        pemSkeleton: "TypeError: ...",
        timestamp: new Date().toISOString(),
        activeFile_hash: "hash123",
        workingDirectory_hash: "dirhash",
        directoryTree: ["tmp", "test.js"],
        packages: ["numpy", "pandas"],
        pythonVersion: "3.10",
        resolutionDepth: 1,
      },
      candidates: [
        {
          id: "cand1",
          vector_similarity: 0.9,
          pemSkeleton: "TypeError: ...",
          timestamp: new Date().toISOString(),
          activeFile_hash: "hashAAA",
          workingDirectory_hash: "dirAAA",
          directoryTree: ["project", "file1.py"],
          packages: ["numpy"],
          pythonVersion: "3.10",
          resolutionDepth: 0,
        },
      ],
    };
  });

  it("should respond to health check", async () => {
    const ok = await rankingService.health();
    expect(ok).toBe(true);
  });

  it("should rank candidates successfully", async () => {
    const res = await rankingService.rank(testRequest);

    expect(res).toHaveProperty("abstain");
    expect(res).toHaveProperty("best");
    expect(res).toHaveProperty("alternates");
    expect(Array.isArray(res.alternates)).toBe(true);

    if (!res.abstain && res.best) {
      expect(res.best.id).toBeDefined();
      expect(res.best.score).toBeGreaterThanOrEqual(0);
      expect(res.best.score).toBeLessThanOrEqual(1);
    }
  });
});