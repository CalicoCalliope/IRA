// tests/dbService.integration.test.ts
import dbService from "../src/services/dbService";
import { PemLogEntry } from "../src/types";
import crypto from "crypto";

describe("Coordinator → DB Service integration", () => {
  let testPem: PemLogEntry;

  beforeAll(() => {
    testPem = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      pem: "TypeError: something went wrong",
      pemType: "TypeError",
      pemSkeleton: "TypeError: ...",
      code: "console.log('hello')",
      username: "testUser",
      activeFile: "test.js",
      workingDirectory: "/tmp",
      directoryTree: ["tmp", "test.js"],
      isFirstOccurrence: true,
      llm: {},
    };
  });

  // Clean DB before each test
  beforeEach(async () => {
    const allPems = await dbService.getPemsByFilter();
    for (const p of allPems) {
      await dbService.deletePemLog(p.id);
    }
  });

  afterEach(async () => {
    const allPems = await dbService.getPemsByFilter();
    for (const p of allPems) {
      await dbService.deletePemLog(p.id);
    }
  });

  it("should ping the DB service", async () => {
    const res = await dbService.pingDb();
    expect(res.status).toBe("up");
  });

  it("should save a PEM log", async () => {
    const res = await dbService.savePemLog(testPem);
    expect(res.status).toBe("ok");
    expect(res.id).toBe(testPem.id);
  });

  it("should fetch a PEM log by ID", async () => {
    await dbService.savePemLog(testPem);
    const pem = await dbService.getPemLog(testPem.id);
    expect(pem.id).toBe(testPem.id);
    expect(pem.username).toBe("testUser");
  });

  it("should fetch PEMs by filter", async () => {
    await dbService.savePemLog(testPem);

    const pemsByUser = await dbService.getPemsByFilter({ username: "testUser" });
    expect(pemsByUser.some(p => p.id === testPem.id)).toBe(true);

    const pemsByType = await dbService.getPemsByFilter({ pemType: "TypeError" });
    expect(pemsByType.some(p => p.id === testPem.id)).toBe(true);

    const pemsByUserAndType = await dbService.getPemsByFilter({
      username: "testUser",
      pemType: "TypeError",
    });
    expect(pemsByUserAndType.some(p => p.id === testPem.id)).toBe(true);

    const allPems = await dbService.getPemsByFilter();
    expect(allPems.some(p => p.id === testPem.id)).toBe(true);
  });

  it("should update a PEM log", async () => {
    await dbService.savePemLog(testPem);
    const res = await dbService.updatePemLog(testPem.id, { pem: "Updated Error" });
    expect(res.status).toBe("ok");

    const updatedPem = await dbService.getPemLog(testPem.id);
    expect(updatedPem.pem).toBe("Updated Error");
  });

  it("should delete a PEM log", async () => {
    await dbService.savePemLog(testPem);
    const res = await dbService.deletePemLog(testPem.id);
    expect(res.status).toBe("ok");

    await expect(dbService.getPemLog(testPem.id)).rejects.toThrow();
  });
});