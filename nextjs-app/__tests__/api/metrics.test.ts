import { describe, it, expect, vi, beforeEach } from "vitest";
import { GET } from "@/app/api/metrics/route";
import { prisma } from "@/lib/db";
import { auth } from "@clerk/nextjs/server";
import { NextRequest } from "next/server";

const mockMetrics = {
  id: 1,
  modelType: "rf_classifier",
  rmse: 0.42,
  accuracy: 0.61,
  f1: 0.58,
  trainedAt: new Date("2026-04-01T10:00:00Z"),
};

describe("GET /api/metrics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns 401 when unauthenticated", async () => {
    vi.mocked(auth).mockReturnValue({ userId: null } as any);
    const req = new NextRequest("http://localhost/api/metrics");
    const res = await GET(req);
    expect(res.status).toBe(401);
  });

  it("returns metrics shape when authenticated", async () => {
    vi.mocked(auth).mockReturnValue({ userId: "user_123" } as any);
    vi.mocked(prisma.pipelineMetrics.findFirst).mockResolvedValue(
      mockMetrics as any,
    );
    const req = new NextRequest("http://localhost/api/metrics");
    const res = await GET(req);
    const data = await res.json();

    expect(res.status).toBe(200);
    expect(data).toHaveProperty("accuracy");
    expect(data).toHaveProperty("f1");
    expect(data).toHaveProperty("rmse");
    expect(data).toHaveProperty("trainedAt");
  });

  it("returns 404 when no metrics exist", async () => {
    vi.mocked(auth).mockReturnValue({ userId: "user_123" } as any);
    vi.mocked(prisma.pipelineMetrics.findFirst).mockResolvedValue(null);
    const req = new NextRequest("http://localhost/api/metrics");
    const res = await GET(req);
    expect(res.status).toBe(404);
  });

  it("returns the latest metrics (ordered by trainedAt desc)", async () => {
    vi.mocked(auth).mockReturnValue({ userId: "user_123" } as any);
    vi.mocked(prisma.pipelineMetrics.findFirst).mockResolvedValue(
      mockMetrics as any,
    );
    const req = new NextRequest("http://localhost/api/metrics");
    await GET(req);

    expect(prisma.pipelineMetrics.findFirst).toHaveBeenCalledWith(
      expect.objectContaining({
        orderBy: expect.objectContaining({ trainedAt: "desc" }),
      }),
    );
  });
});
