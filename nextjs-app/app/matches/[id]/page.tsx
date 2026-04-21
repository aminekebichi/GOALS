import { notFound } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { prisma } from "@/lib/db";

const POS_ORDER = ["forward", "midfielder", "defender", "goalkeeper"];
const POS_LABEL: Record<string, string> = {
  forward: "Forwards",
  midfielder: "Midfielders",
  defender: "Defenders",
  goalkeeper: "Goalkeepers",
};

type MatchPlayer = {
  id: string;
  playerId: string;
  playerName: string;
  teamName: string;
  position: string;
  isMotm: boolean;
  compositeScore: number | null;
  minutesPlayed: number | null;
  goals: number | null;
  assists: number | null;
};

function ScoreBar({ value }: { value: number }) {
  const clamped = Math.max(-3, Math.min(3, value));
  const pct = ((clamped + 3) / 6) * 100;
  const color =
    value >= 0.5 ? "#FF4B44" : value >= -0.5 ? "#C9A84C" : "#4488FF";
  return (
    <div className="flex items-center gap-2 flex-1">
      <div className="flex-1 h-1.5 bg-[#1C2333] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span
        className="text-xs tabular-nums w-10 text-right shrink-0"
        style={{ color }}
      >
        {value >= 0 ? "+" : ""}
        {value.toFixed(2)}
      </span>
    </div>
  );
}

function PlayerList({
  matchId,
  players,
}: {
  matchId: string;
  players: MatchPlayer[];
}) {
  const byPos = POS_ORDER.reduce<Record<string, MatchPlayer[]>>((acc, pos) => {
    acc[pos] = players
      .filter((p) => p.position === pos)
      .sort((a, b) => (b.compositeScore ?? -99) - (a.compositeScore ?? -99));
    return acc;
  }, {});

  return (
    <div className="flex flex-col gap-6">
      {POS_ORDER.map((pos) => {
        const group = byPos[pos];
        if (!group?.length) return null;
        return (
          <div key={pos}>
            <p className="text-xs text-[#8B95A8] uppercase tracking-wider mb-2">
              {POS_LABEL[pos]}
            </p>
            <div className="flex flex-col gap-1">
              {group.map((p) => (
                <Link
                  key={p.id}
                  href={`/matches/${matchId}/players/${p.playerId}`}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#1C2333] transition-colors group"
                >
                  <div
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{
                      backgroundColor: p.isMotm ? "#FF7A00" : "transparent",
                      border: p.isMotm ? "none" : "1px solid #1C2333",
                    }}
                  />
                  <span className="text-sm font-medium text-[#F0F2F8] group-hover:text-white w-40 shrink-0 truncate">
                    {p.playerName}
                    {p.isMotm && (
                      <span className="ml-1.5 text-[10px] text-[#FF7A00] font-bold">
                        MOTM
                      </span>
                    )}
                  </span>
                  <span className="text-xs text-[#8B95A8] w-6 text-center shrink-0">
                    {p.minutesPlayed ? `${Math.round(p.minutesPlayed)}'` : "—"}
                  </span>
                  {p.compositeScore !== null ? (
                    <ScoreBar value={p.compositeScore} />
                  ) : (
                    <span className="text-xs text-[#8B95A8]">—</span>
                  )}
                  <span className="text-xs text-[#8B95A8] shrink-0 group-hover:text-white">
                    →
                  </span>
                </Link>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default async function MatchDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  const [match, allPlayers] = await Promise.all([
    prisma.match.findUnique({ where: { id } }),
    prisma.matchPlayer.findMany({ where: { matchId: id } }),
  ]);
  if (!match) notFound();

  const motm = allPlayers.find((p) => p.isMotm) ?? null;
  const homePlayers = allPlayers.filter((p) => p.teamName === match.homeTeam);
  const awayPlayers = allPlayers.filter((p) => p.teamName === match.awayTeam);

  const isPlayed = match.homeGoals !== null && match.awayGoals !== null;
  const dateStr = match.date.toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const predLabel = match.prediction;
  const predProb = (() => {
    if (!predLabel || match.winProb === null) return null;
    if (predLabel === "Home Win") return match.winProb;
    if (predLabel === "Away Win") return match.lossProb;
    return match.drawProb;
  })();

  const actualOutcome = (() => {
    if (!isPlayed) return null;
    if (match.homeGoals! > match.awayGoals!) return `${match.homeTeam} Win`;
    if (match.awayGoals! > match.homeGoals!) return `${match.awayTeam} Win`;
    return "Draw";
  })();

  const correct =
    predLabel && actualOutcome
      ? predLabel === "Home Win"
        ? actualOutcome === `${match.homeTeam} Win`
        : predLabel === "Away Win"
          ? actualOutcome === `${match.awayTeam} Win`
          : actualOutcome === "Draw"
      : null;

  return (
    <div className="min-h-screen bg-[#0A0E1A]">
      <Navbar />
      <main className="max-w-5xl mx-auto px-4 py-8">
        <Link
          href="/"
          className="text-sm text-[#8B95A8] hover:text-white mb-6 inline-block"
        >
          ← Back to Calendar
        </Link>

        {/* Match header */}
        <div className="bg-[#111827] border border-[#1C2333] rounded-xl p-6 mb-6">
          <p className="text-xs text-[#8B95A8] mb-4">{dateStr}</p>
          <div className="flex items-center justify-between gap-4 mb-5">
            <span className="text-xl font-bold text-right flex-1">
              {match.homeTeam}
            </span>
            <div className="text-center">
              {isPlayed ? (
                <span className="text-3xl font-bold tabular-nums">
                  {match.homeGoals} – {match.awayGoals}
                </span>
              ) : (
                <span className="text-xl font-bold text-[#8B95A8]">vs</span>
              )}
              <p className="text-xs text-[#8B95A8] mt-1">
                {isPlayed ? "Full Time" : "Upcoming"}
              </p>
            </div>
            <span className="text-xl font-bold flex-1">{match.awayTeam}</span>
          </div>

          {predLabel && predProb !== null && (
            <div className="border-t border-[#1C2333] pt-4 flex flex-wrap gap-4 items-center justify-between">
              <div>
                <p className="text-xs text-[#8B95A8] mb-1">Model prediction</p>
                <p className="font-semibold text-[#FF7A00]">
                  {predLabel === "Home Win"
                    ? match.homeTeam
                    : predLabel === "Away Win"
                      ? match.awayTeam
                      : "Draw"}
                  <span className="text-sm text-[#8B95A8] font-normal ml-1">
                    ({Math.round(predProb * 100)}% confidence)
                  </span>
                </p>
              </div>
              {isPlayed && actualOutcome && (
                <div className="text-right">
                  <p className="text-xs text-[#8B95A8] mb-1">Actual result</p>
                  <p
                    className={`font-semibold ${correct ? "text-emerald-400" : "text-[#FF4B44]"}`}
                  >
                    {actualOutcome}
                    <span
                      className={`ml-2 text-xs px-1.5 py-0.5 rounded font-bold ${correct ? "bg-emerald-400/15 text-emerald-400" : "bg-[#FF4B44]/15 text-[#FF4B44]"}`}
                    >
                      {correct ? "✓ Correct" : "✗ Wrong"}
                    </span>
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* MOTM */}
        {motm && (
          <Link
            href={`/matches/${id}/players/${motm.playerId}`}
            className="block bg-gradient-to-r from-[#FF7A00]/20 to-[#FF4B44]/10 border border-[#FF7A00]/40 rounded-xl p-5 mb-6 hover:border-[#FF7A00]/70 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[#FF7A00] font-bold uppercase tracking-wider mb-1">
                  Man of the Match
                </p>
                <p className="text-xl font-bold text-white">
                  {motm.playerName}
                </p>
                <p className="text-sm text-[#8B95A8] mt-0.5">
                  {motm.teamName} ·{" "}
                  {motm.position.charAt(0).toUpperCase() +
                    motm.position.slice(1)}
                </p>
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold text-[#FF7A00]">
                  {motm.compositeScore !== null && motm.compositeScore >= 0
                    ? "+"
                    : ""}
                  {motm.compositeScore?.toFixed(2)}
                </p>
                <p className="text-xs text-[#8B95A8] mt-0.5">composite score</p>
                <p className="text-xs text-[#8B95A8] mt-2">View stats →</p>
              </div>
            </div>
          </Link>
        )}

        {/* Player rosters */}
        <h2 className="text-lg font-bold mb-1">Player Performance</h2>
        <p className="text-xs text-[#8B95A8] mb-5">
          Click any player to view their match stats. Bars show composite
          z-score for this game.
        </p>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <h3 className="font-bold text-[#FF7A00] mb-4">{match.homeTeam}</h3>
            <PlayerList matchId={id} players={homePlayers} />
          </div>
          <div>
            <h3 className="font-bold text-[#FF7A00] mb-4">{match.awayTeam}</h3>
            <PlayerList matchId={id} players={awayPlayers} />
          </div>
        </div>
      </main>
    </div>
  );
}
