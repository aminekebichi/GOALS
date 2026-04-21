/**
 * Seed script: reads ML pipeline output and populates Neon PostgreSQL.
 *
 * Prerequisites:
 *   1. Run Python ML pipeline (goals_app/) to generate predictions
 *   2. Export data: python scripts/export_for_seed.py > scripts/seed_data.json
 *   3. Set DATABASE_URL in .env.local
 *   4. Run: npx ts-node scripts/seed_db.ts
 */

import { PrismaClient } from '@prisma/client';
import * as fs from 'fs';
import * as path from 'path';

const prisma = new PrismaClient();

interface MatchPlayerSeed {
  id: string;
  matchId: string;
  playerId: string;
  playerName: string;
  teamName: string;
  position: string;
  isMotm: boolean;
  compositeScore?: number;
  minutesPlayed?: number;
  goals?: number;
  assists?: number;
  xGoals?: number;
  xAssists?: number;
  shotsOnTarget?: number;
  shotsOffTarget?: number;
  chancesCreated?: number;
  passAccuracy?: number;
  dribbles?: number;
  interceptions?: number;
  clearances?: number;
  recoveries?: number;
  aerialsWon?: number;
  saves?: number;
  saveRate?: number;
  xGotFaced?: number;
  goalsPrevented?: number;
}

interface SeedData {
  matches: {
    id: string;
    homeTeam: string;
    awayTeam: string;
    date: string;
    homeGoals?: number;
    awayGoals?: number;
    season: string;
    winProb?: number;
    drawProb?: number;
    lossProb?: number;
    prediction?: string;
  }[];
  players: {
    id: string;
    name: string;
    team: string;
    position: string;
    attScore?: number;
    midScore?: number;
    defScore?: number;
    gkScore?: number;
    season: string;
  }[];
  metrics: {
    modelType: string;
    rmse?: number;
    accuracy?: number;
    f1?: number;
  }[];
  matchPlayers: MatchPlayerSeed[];
}

async function main() {
  const dataPath = path.join(__dirname, 'seed_data.json');

  if (!fs.existsSync(dataPath)) {
    console.error('seed_data.json not found. Run: python scripts/export_for_seed.py > scripts/seed_data.json');
    process.exit(1);
  }

  const data: SeedData = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));

  console.log(`Seeding ${data.matches.length} matches...`);
  for (const match of data.matches) {
    await prisma.match.upsert({
      where: { id: match.id },
      update: match,
      create: { ...match, date: new Date(match.date) },
    });
  }

  console.log(`Seeding ${data.players.length} players...`);
  for (const player of data.players) {
    await prisma.player.upsert({
      where: { id: player.id },
      update: player,
      create: player,
    });
  }

  console.log(`Seeding ${data.matchPlayers?.length ?? 0} match player records...`);
  const BATCH = 100;
  const mp = data.matchPlayers ?? [];
  for (let i = 0; i < mp.length; i += BATCH) {
    const batch = mp.slice(i, i + BATCH);
    await Promise.all(
      batch.map((p) =>
        prisma.matchPlayer.upsert({ where: { id: p.id }, update: p, create: p })
      )
    );
  }

  console.log(`Seeding ${data.metrics.length} metrics records...`);
  for (const metric of data.metrics) {
    await prisma.pipelineMetrics.create({ data: metric });
  }

  console.log('Seed complete.');
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
