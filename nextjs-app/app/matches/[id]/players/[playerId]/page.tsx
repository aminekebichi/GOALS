import { notFound } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { prisma } from "@/lib/db";

function StatRow({
  label,
  value,
  unit = "",
}: {
  label: string;
  value: number | null | undefined;
  unit?: string;
}) {
  if (value === null || value === undefined) return null;
  const display = Number.isInteger(value) ? value : value.toFixed(2);
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-[#1C2333] last:border-0">
      <span className="text-sm text-[#8B95A8]">{label}</span>
      <span className="text-sm font-semibold text-[#F0F2F8] tabular-nums">
        {display}
        {unit}
      </span>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-[#111827] border border-[#1C2333] rounded-xl p-5 mb-4">
      <h3 className="text-xs text-[#8B95A8] uppercase tracking-wider mb-3 font-bold">
        {title}
      </h3>
      {children}
    </div>
  );
}

export default async function PlayerGamePage({
  params,
}: {
  params: Promise<{ id: string; playerId: string }>;
}) {
  const { id: matchId, playerId } = await params;

  const [match, player] = await Promise.all([
    prisma.match.findUnique({ where: { id: matchId } }),
    prisma.matchPlayer.findUnique({ where: { id: `${matchId}_${playerId}` } }),
  ]);

  if (!match || !player) notFound();

  const isGk = player.position === "goalkeeper";
  const scoreColor =
    (player.compositeScore ?? 0) >= 0.5
      ? "#FF4B44"
      : (player.compositeScore ?? 0) >= -0.5
        ? "#C9A84C"
        : "#4488FF";

  const posLabel =
    player.position.charAt(0).toUpperCase() + player.position.slice(1);

  return (
    <div className="min-h-screen bg-[#0A0E1A]">
      <Navbar />
      <main className="max-w-2xl mx-auto px-4 py-8">
        <Link
          href={`/matches/${matchId}`}
          className="text-sm text-[#8B95A8] hover:text-white mb-6 inline-block"
        >
          ← {match.homeTeam} vs {match.awayTeam}
        </Link>

        {/* Player header */}
        <div className="bg-[#111827] border border-[#1C2333] rounded-xl p-6 mb-6">
          <div className="flex items-start justify-between">
            <div>
              {player.isMotm && (
                <p className="text-xs text-[#FF7A00] font-bold uppercase tracking-wider mb-1">
                  ⭐ Man of the Match
                </p>
              )}
              <h1 className="text-2xl font-bold text-white">
                {player.playerName}
              </h1>
              <p className="text-sm text-[#8B95A8] mt-1">
                {player.teamName} · {posLabel}
              </p>
              <p className="text-xs text-[#8B95A8] mt-1">
                {match.date.toLocaleDateString("en-GB", {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                })}
                {" · "}
                {match.homeTeam} {match.homeGoals ?? "?"} –{" "}
                {match.awayGoals ?? "?"} {match.awayTeam}
              </p>
            </div>
            <div className="text-right">
              <p
                className="text-3xl font-bold tabular-nums"
                style={{ color: scoreColor }}
              >
                {(player.compositeScore ?? 0) >= 0 ? "+" : ""}
                {player.compositeScore?.toFixed(2) ?? "—"}
              </p>
              <p className="text-xs text-[#8B95A8] mt-0.5">composite score</p>
              {player.minutesPlayed !== null && (
                <p className="text-xs text-[#8B95A8] mt-1">
                  {Math.round(player.minutesPlayed ?? 0)} min played
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Stats breakdown */}
        {isGk ? (
          <>
            <Section title="Goalkeeping">
              <StatRow label="Saves" value={player.saves} />
              <StatRow
                label="Save rate"
                value={player.saveRate !== null ? player.saveRate! * 100 : null}
                unit="%"
              />
              <StatRow
                label="Goals prevented (xGOT − conceded)"
                value={player.goalsPrevented}
              />
              <StatRow label="xG on target faced" value={player.xGotFaced} />
            </Section>
            <Section title="Distribution & Defending">
              <StatRow
                label="Pass accuracy"
                value={
                  player.passAccuracy !== null
                    ? player.passAccuracy! * 100
                    : null
                }
                unit="%"
              />
              <StatRow label="Clearances" value={player.clearances} />
              <StatRow label="Interceptions" value={player.interceptions} />
              <StatRow label="Recoveries" value={player.recoveries} />
              <StatRow label="Aerial duels won" value={player.aerialsWon} />
            </Section>
          </>
        ) : (
          <>
            <Section title="Attack">
              <StatRow label="Goals" value={player.goals} />
              <StatRow label="Assists" value={player.assists} />
              <StatRow label="Expected goals (xG)" value={player.xGoals} />
              <StatRow label="Expected assists (xA)" value={player.xAssists} />
              <StatRow label="Shots on target" value={player.shotsOnTarget} />
              <StatRow label="Shots off target" value={player.shotsOffTarget} />
              <StatRow label="Chances created" value={player.chancesCreated} />
            </Section>
            <Section title="Possession">
              <StatRow
                label="Pass accuracy"
                value={
                  player.passAccuracy !== null
                    ? player.passAccuracy! * 100
                    : null
                }
                unit="%"
              />
              <StatRow label="Successful dribbles" value={player.dribbles} />
            </Section>
            <Section title="Defending">
              <StatRow label="Interceptions" value={player.interceptions} />
              <StatRow label="Clearances" value={player.clearances} />
              <StatRow label="Recoveries" value={player.recoveries} />
              <StatRow label="Aerial duels won" value={player.aerialsWon} />
            </Section>
          </>
        )}
      </main>
    </div>
  );
}
