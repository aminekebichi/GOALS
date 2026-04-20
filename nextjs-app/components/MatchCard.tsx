interface Match {
  id: string;
  homeTeam: string;
  awayTeam: string;
  date: string;
  homeGoals: number | null;
  awayGoals: number | null;
  winProb: number | null;
  drawProb: number | null;
  lossProb: number | null;
  prediction: string | null;
}

export default function MatchCard({ match }: { match: Match }) {
  const date = new Date(match.date);
  const isPlayed = match.homeGoals !== null;

  return (
    <div
      data-testid="match-card"
      className="bg-[#111827] border border-[#1C2333] rounded-xl p-5 hover:border-[#FF4B44]/40 transition-colors"
    >
      <div className="flex justify-between items-start mb-4">
        <span className="text-xs text-[#8B95A8]">
          {date.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })}
        </span>
        {isPlayed ? (
          <span className="text-xs bg-[#1C2333] text-[#8B95A8] px-2 py-1 rounded">FT</span>
        ) : (
          <span className="text-xs bg-[#FF4B44]/20 text-[#FF4B44] px-2 py-1 rounded">
            {date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between gap-4 mb-4">
        <span className="font-semibold text-sm flex-1 text-right">{match.homeTeam}</span>
        {isPlayed ? (
          <span className="text-2xl font-bold text-[#FF4B44] tabular-nums">
            {match.homeGoals} – {match.awayGoals}
          </span>
        ) : (
          <span className="text-lg font-bold text-[#8B95A8]">vs</span>
        )}
        <span className="font-semibold text-sm flex-1">{match.awayTeam}</span>
      </div>

      {match.winProb !== null && (
        <ProbabilityBar win={match.winProb} draw={match.drawProb!} loss={match.lossProb!} />
      )}
    </div>
  );
}

function ProbabilityBar({ win, draw, loss }: { win: number; draw: number; loss: number }) {
  const fmt = (v: number) => `${Math.round(v * 100)}%`;
  return (
    <div>
      <div className="flex h-2 rounded-full overflow-hidden">
        <div className="bg-[#FF4B44]" style={{ width: `${win * 100}%` }} />
        <div className="bg-[#C9A84C]" style={{ width: `${draw * 100}%` }} />
        <div className="bg-[#4488FF]" style={{ width: `${loss * 100}%` }} />
      </div>
      <div className="flex justify-between mt-1 text-xs text-[#8B95A8]">
        <span className="text-[#FF4B44]">W {fmt(win)}</span>
        <span className="text-[#C9A84C]">D {fmt(draw)}</span>
        <span className="text-[#4488FF]">L {fmt(loss)}</span>
      </div>
    </div>
  );
}
