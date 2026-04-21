import { describe, it, expect, vi, beforeEach } from "vitest";
import { GET } from "@/app/api/players/route";
import { prisma } from "@/lib/db";
import { auth } from "@clerk/nextjs/server";
import { NextRequest } from "next/server";

const mockPlayers = [
  {
    id: "player-1",
    name: "Bukayo Saka",
    team: "Arsenal",
    position: "ATT",
    attScore: 1.85,
    midScore: 0.92,
    defScore: 0.3,
    gkScore: null,
    season: "2024_2025",
  },
];

describe("GET /api/players", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns 401 when unauthenticated", async () => {
    vi.mocked(auth).mockReturnValue({ userId: null } as any);
    const req = new NextRequest("http://localhost/api/players");
    const res = await GET(req);
    expect(res.status).toBe(401);
  });

  it("returns players when authenticated", async () => {
    vi.mocked(auth).mockReturnValue({ userId: "user_123" } as any);
    vi.mocked(prisma.player.findMany).mockResolvedValue(mockPlayers as any);
    const req = new NextRequest("http://localhost/api/players");
    const res = await GET(req);
    const data = await res.json();

    expect(res.status).toBe(200);
    expect(data).toHaveProperty("players");
    expect(Array.isArray(data.players)).toBe(true);
  });

  it("returns composite score fields", async () => {
    vi.mocked(auth).mockReturnValue({ userId: "user_123" } as any);
    vi.mocked(prisma.player.findMany).mockResolvedValue(mockPlayers as any);
    const req = new NextRequest("http://localhost/api/players");
    const res = await GET(req);
    const data = await res.json();

    const player = data.players[0];
    expect(player).toHaveProperty("attScore");
    expect(player).toHaveProperty("midScore");
    expect(player).toHaveProperty("defScore");
    expect(player).toHaveProperty("gkScore");
  });

  it("filters by position query param", async () => {
    vi.mocked(auth).mockReturnValue({ userId: "user_123" } as any);
    vi.mocked(prisma.player.findMany).mockResolvedValue([] as any);
    const req = new NextRequest("http://localhost/api/players?position=ATT");
    await GET(req);

    expect(prisma.player.findMany).toHaveBeenCalledWith(
      expect.objectContaining({
        where: expect.objectContaining({ position: "ATT" }),
      }),
    );
  });

  it("filters by team query param", async () => {
    vi.mocked(auth).mockReturnValue({ userId: "user_123" } as any);
    vi.mocked(prisma.player.findMany).mockResolvedValue([] as any);
    const req = new NextRequest("http://localhost/api/players?team=Arsenal");
    await GET(req);

    expect(prisma.player.findMany).toHaveBeenCalledWith(
      expect.objectContaining({
        where: expect.objectContaining({ team: "Arsenal" }),
      }),
    );
  });
});
