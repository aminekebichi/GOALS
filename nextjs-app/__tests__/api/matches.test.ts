import { describe, it, expect, vi, beforeEach } from 'vitest';
import { GET } from '@/app/api/matches/route';
import { prisma } from '@/lib/db';
import { NextRequest } from 'next/server';

const mockMatches = [
  {
    id: 'match-1',
    homeTeam: 'Arsenal',
    awayTeam: 'Chelsea',
    date: new Date('2024-09-01T15:00:00Z'),
    homeGoals: 2,
    awayGoals: 1,
    season: '2024_2025',
    winProb: 0.55,
    drawProb: 0.25,
    lossProb: 0.2,
    prediction: 'home_win',
  },
];

describe('GET /api/matches', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns matches with correct shape', async () => {
    vi.mocked(prisma.match.findMany).mockResolvedValue(mockMatches as any);
    const req = new NextRequest('http://localhost/api/matches');
    const res = await GET(req);
    const data = await res.json();

    expect(res.status).toBe(200);
    expect(data).toHaveProperty('matches');
    expect(Array.isArray(data.matches)).toBe(true);
  });

  it('returns match fields including probabilities', async () => {
    vi.mocked(prisma.match.findMany).mockResolvedValue(mockMatches as any);
    const req = new NextRequest('http://localhost/api/matches');
    const res = await GET(req);
    const data = await res.json();

    const match = data.matches[0];
    expect(match).toHaveProperty('id');
    expect(match).toHaveProperty('homeTeam');
    expect(match).toHaveProperty('awayTeam');
    expect(match).toHaveProperty('winProb');
    expect(match).toHaveProperty('drawProb');
    expect(match).toHaveProperty('lossProb');
    expect(match).toHaveProperty('prediction');
  });

  it('filters by season query param', async () => {
    vi.mocked(prisma.match.findMany).mockResolvedValue([] as any);
    const req = new NextRequest('http://localhost/api/matches?season=2023_2024');
    await GET(req);

    expect(prisma.match.findMany).toHaveBeenCalledWith(
      expect.objectContaining({
        where: expect.objectContaining({ season: '2023_2024' }),
      })
    );
  });

  it('returns 200 with no season filter (all seasons)', async () => {
    vi.mocked(prisma.match.findMany).mockResolvedValue(mockMatches as any);
    const req = new NextRequest('http://localhost/api/matches');
    const res = await GET(req);
    expect(res.status).toBe(200);
  });
});
