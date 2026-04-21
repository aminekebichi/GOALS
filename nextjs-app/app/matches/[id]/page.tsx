import { notFound } from 'next/navigation';
import Link from 'next/link';
import Navbar from '@/components/Navbar';
import { prisma } from '@/lib/db';

const POS_ORDER = ['forward', 'midfielder', 'defender', 'goalkeeper'];
const POS_LABEL: Record<string, string> = {
  forward: 'Forwards',
  midfielder: 'Midfielders',
  defender: 'Defenders',
  goalkeeper: 'Goalkeepers',
};

function scoreForPosition(pos: string, p: { attScore: number | null; midScore: number | null; defScore: number | null; gkScore: number | null }) {
  if (pos === 'forward') return p.attScore;
  if (pos === 'midfielder') return p.midScore;
  if (pos === 'defender') return p.defScore;
  if (pos === 'goalkeeper') return p.gkScore;
  return null;
}

function ScoreBar({ value }: { value: number }) {
  const clamped = Math.max(-3, Math.min(3, value));
  const pct = ((clamped + 3) / 6) * 100;
  const color = value >= 0.5 ? '#FF4B44' : value >= -0.5 ? '#C9A84C' : '#4488FF';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-[#1C2333] rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs tabular-nums w-10 text-right" style={{ color }}>
        {value >= 0 ? '+' : ''}{value.toFixed(2)}
      </span>
    </div>
  );
}

function TeamRoster({
  team,
  players,
  side,
}: {
  team: string;
  players: { id: string; name: string; position: string; attScore: number | null; midScore: number | null; defScore: number | null; gkScore: number | null }[];
  side: 'home' | 'away';
}) {
  const byPos = POS_ORDER.reduce<Record<string, typeof players>>((acc, pos) => {
    acc[pos] = players.filter((p) => p.position === pos).sort((a, b) => {
      const sa = scoreForPosition(pos, a) ?? -99;
      const sb = scoreForPosition(pos, b) ?? -99;
      return sb - sa;
    });
    return acc;
  }, {});

  return (
    <div className={`flex-1 ${side === 'away' ? 'text-right' : ''}`}>
      <h3 className="font-bold text-lg mb-4 text-[#FF7A00]">{team}</h3>
      {POS_ORDER.map((pos) => {
        const group = byPos[pos];
        if (!group || group.length === 0) return null;
        return (
          <div key={pos} className="mb-5">
            <p className="text-xs text-[#8B95A8] uppercase tracking-wider mb-2">{POS_LABEL[pos]}</p>
            <div className="flex flex-col gap-2">
              {group.map((p) => {
                const score = scoreForPosition(pos, p);
                return (
                  <div key={p.id} className={`flex flex-col gap-1 ${side === 'away' ? 'items-end' : ''}`}>
                    <span className="text-sm font-medium text-[#F0F2F8]">{p.name}</span>
                    {score !== null ? (
                      <div className={`w-full max-w-[200px] ${side === 'away' ? 'ml-auto' : ''}`}>
                        <ScoreBar value={score} />
                      </div>
                    ) : (
                      <span className="text-xs text-[#8B95A8]">—</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
      {players.length === 0 && (
        <p className="text-sm text-[#8B95A8]">No player data available</p>
      )}
    </div>
  );
}

export default async function MatchDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  const match = await prisma.match.findUnique({ where: { id } });
  if (!match) notFound();

  const [homePlayers, awayPlayers] = await Promise.all([
    prisma.player.findMany({
      where: { team: match.homeTeam, season: '2024_2025' },
      orderBy: { name: 'asc' },
    }),
    prisma.player.findMany({
      where: { team: match.awayTeam, season: '2024_2025' },
      orderBy: { name: 'asc' },
    }),
  ]);

  const isPlayed = match.homeGoals !== null && match.awayGoals !== null;
  const date = match.date.toLocaleDateString('en-GB', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  });

  const predLabel = match.prediction;
  const predProb = (() => {
    if (!predLabel || match.winProb === null) return null;
    if (predLabel === 'Home Win') return match.winProb;
    if (predLabel === 'Away Win') return match.lossProb;
    return match.drawProb;
  })();

  const actualOutcome = (() => {
    if (!isPlayed) return null;
    if (match.homeGoals! > match.awayGoals!) return `${match.homeTeam} Win`;
    if (match.awayGoals! > match.homeGoals!) return `${match.awayTeam} Win`;
    return 'Draw';
  })();

  const correct = (() => {
    if (!isPlayed || !predLabel) return null;
    if (predLabel === 'Home Win') return actualOutcome === `${match.homeTeam} Win`;
    if (predLabel === 'Away Win') return actualOutcome === `${match.awayTeam} Win`;
    return actualOutcome === 'Draw';
  })();

  return (
    <div className="min-h-screen bg-[#0A0E1A]">
      <Navbar />
      <main className="max-w-5xl mx-auto px-4 py-8">
        {/* Back */}
        <Link href="/" className="text-sm text-[#8B95A8] hover:text-white mb-6 inline-block">
          ← Back to Calendar
        </Link>

        {/* Match header */}
        <div className="bg-[#111827] border border-[#1C2333] rounded-xl p-6 mb-8">
          <p className="text-xs text-[#8B95A8] mb-4">{date}</p>

          <div className="flex items-center justify-between gap-4 mb-6">
            <span className="text-xl font-bold text-right flex-1">{match.homeTeam}</span>
            <div className="text-center">
              {isPlayed ? (
                <span className="text-3xl font-bold tabular-nums">
                  {match.homeGoals} – {match.awayGoals}
                </span>
              ) : (
                <span className="text-xl font-bold text-[#8B95A8]">vs</span>
              )}
              <p className="text-xs text-[#8B95A8] mt-1">{isPlayed ? 'Full Time' : 'Upcoming'}</p>
            </div>
            <span className="text-xl font-bold flex-1">{match.awayTeam}</span>
          </div>

          {/* Prediction row */}
          {predLabel && predProb !== null && (
            <div className="border-t border-[#1C2333] pt-4 flex flex-wrap gap-4 items-center justify-between">
              <div>
                <p className="text-xs text-[#8B95A8] mb-1">Model prediction</p>
                <p className="font-semibold text-[#FF7A00]">
                  {predLabel === 'Home Win' ? match.homeTeam : predLabel === 'Away Win' ? match.awayTeam : 'Draw'}
                  {' '}
                  <span className="text-sm text-[#8B95A8] font-normal">
                    ({Math.round(predProb * 100)}% confidence)
                  </span>
                </p>
              </div>
              {isPlayed && actualOutcome && (
                <div className="text-right">
                  <p className="text-xs text-[#8B95A8] mb-1">Actual result</p>
                  <p className={`font-semibold ${correct ? 'text-emerald-400' : 'text-[#FF4B44]'}`}>
                    {actualOutcome}
                    <span className={`ml-2 text-xs px-1.5 py-0.5 rounded font-bold ${correct ? 'bg-emerald-400/15 text-emerald-400' : 'bg-[#FF4B44]/15 text-[#FF4B44]'}`}>
                      {correct ? '✓ Correct' : '✗ Wrong'}
                    </span>
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Player rosters */}
        <h2 className="text-xl font-bold mb-4">Player Performance (2024/25)</h2>
        <p className="text-sm text-[#8B95A8] mb-6">
          Composite z-scores: positive = above average, negative = below average. Bars show relative performance within each position.
        </p>

        <div className="flex gap-8">
          <TeamRoster team={match.homeTeam} players={homePlayers} side="home" />
          <div className="w-px bg-[#1C2333]" />
          <TeamRoster team={match.awayTeam} players={awayPlayers} side="away" />
        </div>
      </main>
    </div>
  );
}
