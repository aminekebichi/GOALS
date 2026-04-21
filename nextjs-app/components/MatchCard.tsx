import Link from 'next/link';

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

function getPredictedTeam(match: Match): { label: string; prob: number } | null {
  if (!match.prediction || match.winProb === null) return null;
  if (match.prediction === 'Home Win') {
    return { label: match.homeTeam, prob: match.winProb };
  }
  if (match.prediction === 'Away Win') {
    return { label: match.awayTeam, prob: match.lossProb! };
  }
  return { label: 'Draw', prob: match.drawProb! };
}

function getActualOutcome(match: Match): string | null {
  if (match.homeGoals === null || match.awayGoals === null) return null;
  if (match.homeGoals > match.awayGoals) return `${match.homeTeam} Win`;
  if (match.awayGoals > match.homeGoals) return `${match.awayTeam} Win`;
  return 'Draw';
}

function predictionCorrect(match: Match): boolean | null {
  const actual = getActualOutcome(match);
  if (!actual || !match.prediction) return null;
  const predicted = getPredictedTeam(match);
  if (!predicted) return null;
  if (match.prediction === 'Home Win') return actual === `${match.homeTeam} Win`;
  if (match.prediction === 'Away Win') return actual === `${match.awayTeam} Win`;
  return actual === 'Draw';
}

export default function MatchCard({ match }: { match: Match }) {
  const date = new Date(match.date);
  const isPlayed = match.homeGoals !== null && match.awayGoals !== null;
  const predicted = getPredictedTeam(match);
  const actualOutcome = getActualOutcome(match);
  const correct = predictionCorrect(match);

  const dateStr = date.toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });

  return (
    <Link
      href={`/matches/${match.id}`}
      data-testid="match-card"
      className="bg-[#111827] border border-[#1C2333] rounded-xl p-5 hover:border-[#FF4B44]/40 transition-colors flex flex-col gap-4 cursor-pointer"
    >
      {/* Header row */}
      <div className="flex justify-between items-center">
        <span className="text-xs text-[#8B95A8]">{dateStr}</span>
        {isPlayed ? (
          <span className="text-xs bg-[#1C2333] text-[#8B95A8] px-2 py-1 rounded font-medium">
            Full Time
          </span>
        ) : (
          <span className="text-xs bg-[#FF4B44]/20 text-[#FF4B44] px-2 py-1 rounded font-medium">
            Upcoming
          </span>
        )}
      </div>

      {/* Teams + score */}
      <div className="flex items-center justify-between gap-3">
        <span className="font-semibold text-sm flex-1 text-right leading-tight">{match.homeTeam}</span>
        <div className="flex flex-col items-center min-w-[60px]">
          {isPlayed ? (
            <span className="text-2xl font-bold text-white tabular-nums">
              {match.homeGoals}&nbsp;–&nbsp;{match.awayGoals}
            </span>
          ) : (
            <span className="text-sm font-bold text-[#8B95A8]">vs</span>
          )}
        </div>
        <span className="font-semibold text-sm flex-1 leading-tight">{match.awayTeam}</span>
      </div>

      {/* Prediction */}
      {predicted && (
        <div className="border-t border-[#1C2333] pt-3 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[#8B95A8]">Predicted winner</span>
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-semibold text-[#FF7A00]">{predicted.label}</span>
              <span className="text-xs text-[#8B95A8]">
                ({Math.round(predicted.prob * 100)}% confidence)
              </span>
            </div>
          </div>

          {/* Actual outcome for played matches */}
          {isPlayed && actualOutcome && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-[#8B95A8]">Actual result</span>
              <div className="flex items-center gap-1.5">
                <span
                  className={`text-sm font-semibold ${
                    correct === true ? 'text-emerald-400' : 'text-[#FF4B44]'
                  }`}
                >
                  {actualOutcome}
                </span>
                <span
                  className={`text-xs px-1.5 py-0.5 rounded font-bold ${
                    correct === true
                      ? 'bg-emerald-400/15 text-emerald-400'
                      : 'bg-[#FF4B44]/15 text-[#FF4B44]'
                  }`}
                >
                  {correct === true ? '✓ Correct' : '✗ Wrong'}
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </Link>
  );
}
