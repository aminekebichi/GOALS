import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';
import { prisma } from '@/lib/db';

export async function GET(req: NextRequest) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { searchParams } = req.nextUrl;
  const position = searchParams.get('position') ?? undefined;
  const team = searchParams.get('team') ?? undefined;
  const season = searchParams.get('season') ?? undefined;

  const where: Record<string, string> = {};
  if (position) where.position = position;
  if (team) where.team = team;
  if (season) where.season = season;

  const players = await prisma.player.findMany({
    where,
    orderBy: { name: 'asc' },
  });

  return NextResponse.json({ players });
}
