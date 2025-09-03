import request from "supertest";
import { app, connectMongo, getPemCollection } from "../src/index";
import { PemLogEntry } from "../src/types";
import crypto from "crypto";

let pemCollection: ReturnType<typeof getPemCollection>;

// Helper to generate test PEM
function createTestPem(overrides: Partial<PemLogEntry> = {}): PemLogEntry {
  return {
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    pem: "TestError: something went wrong",
    pemType: "TestError",
    pemSkeleton: "TestError: ...",
    code: "print('hello')",
    username: "testuser",
    activeFile: "test.py",
    workingDirectory: "/tmp",
    directoryTree: ["tmp", "test.py"],
    isFirstOccurrence: true,
    llm: {},
    ...overrides,
  };
}

beforeAll(async () => {
  await connectMongo("iraLogsTest"); // use a separate test DB
  pemCollection = getPemCollection();
});

afterEach(async () => {
  await pemCollection.deleteMany({});
});

afterAll(async () => {
  const client = pemCollection.s.db.client;
  await client.close();
});

describe("DB Service Full Integration Tests", () => {

  it("GET /health returns server status", async () => {
    const res = await request(app).get("/health");
    expect(res.status).toBe(200);
    expect(res.body.status).toBe("up");
  });

  it("POST /pems creates a new PEM", async () => {
    const pem = createTestPem();
    const res = await request(app).post("/pems").send(pem);
    expect(res.status).toBe(200);
    expect(res.body.status).toBe("ok");
    expect(res.body.id).toBe(pem.id);
  });

  it("GET /pems/:id retrieves a PEM by ID", async () => {
    const pem = createTestPem();
    await pemCollection.insertOne(pem);

    const res = await request(app).get(`/pems/${pem.id}`);
    expect(res.status).toBe(200);
    expect(res.body.status).toBe("ok");
    expect(res.body.data.id).toBe(pem.id);
  });

  describe("GET /pems with filters", () => {
    it("returns only PEMs for a specific username", async () => {
      const pem1 = createTestPem({ username: "user1" });
      const pem2 = createTestPem({ username: "user2" });
      await pemCollection.insertMany([pem1, pem2]);

      const res = await request(app).get("/pems").query({ username: "user1" });
      expect(res.status).toBe(200);
      expect(res.body.data.length).toBe(1);
      expect(res.body.data[0].username).toBe("user1");
    });

    it("returns only PEMs for a specific pemType", async () => {
      const pem1 = createTestPem({ pemType: "TypeA" });
      const pem2 = createTestPem({ pemType: "TypeB" });
      await pemCollection.insertMany([pem1, pem2]);

      const res = await request(app).get("/pems").query({ pemType: "TypeB" });
      expect(res.status).toBe(200);
      expect(res.body.data.length).toBe(1);
      expect(res.body.data[0].pemType).toBe("TypeB");
    });

    it("returns PEMs matching both username and pemType", async () => {
      const pem1 = createTestPem({ username: "user1", pemType: "TypeA" });
      const pem2 = createTestPem({ username: "user1", pemType: "TypeB" });
      await pemCollection.insertMany([pem1, pem2]);

      const res = await request(app)
        .get("/pems")
        .query({ username: "user1", pemType: "TypeA" });
      expect(res.status).toBe(200);
      expect(res.body.data.length).toBe(1);
      expect(res.body.data[0].username).toBe("user1");
      expect(res.body.data[0].pemType).toBe("TypeA");
    });

    it("returns all PEMs if no filter is provided", async () => {
      const pem1 = createTestPem();
      const pem2 = createTestPem();
      await pemCollection.insertMany([pem1, pem2]);

      const res = await request(app).get("/pems");
      expect(res.status).toBe(200);
      expect(res.body.data.length).toBe(2);
    });
  });

  it("PATCH /pems/:id updates a PEM", async () => {
    const pem = createTestPem();
    await pemCollection.insertOne(pem);

    const res = await request(app)
      .patch(`/pems/${pem.id}`)
      .send({ pem: "Updated Error", llm: { hint: "Updated hint" } });

    expect(res.status).toBe(200);
    expect(res.body.status).toBe("ok");

    const getRes = await request(app).get(`/pems/${pem.id}`);
    expect(getRes.body.data.pem).toBe("Updated Error");
    expect(getRes.body.data.llm.hint).toBe("Updated hint");
  });

  it("DELETE /pems/:id deletes a PEM", async () => {
    const pem = createTestPem();
    await pemCollection.insertOne(pem);

    const res = await request(app).delete(`/pems/${pem.id}`);
    expect(res.status).toBe(200);
    expect(res.body.status).toBe("ok");

    const getRes = await request(app).get(`/pems/${pem.id}`);
    expect(getRes.status).toBe(404);
  });

});