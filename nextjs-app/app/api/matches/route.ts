import { NextRequest, NextResponse } from 'next/server';
import { prisma } from '@/lib/db';

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const season = searchParams.get('season') ?? undefined;

  const where = season ? { season } : {};

  const matches = await prisma.match.findMany({
    where,
    orderBy: { date: 'desc' },
  });

  return NextResponse.json({ matches });
}
