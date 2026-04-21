interface Player {
  id: string;
  name: string;
  team: string;
  position: string;
  attScore: number | null;
  midScore: number | null;
  defScore: number | null;
  gkScore: number | null;
}

const POSITION_LABELS: Record<string, string> = {
  ATT: "Forward",
  MID: "Midfielder",
  DEF: "Defender",
  GK: "Goalkeeper",
};

export default function PlayerRow({ player }: { player: Player }) {
  const score =
    player.attScore ??
    player.midScore ??
    player.defScore ??
    player.gkScore ??
    0;
  const scoreColor =
    score > 1.5
      ? "text-[#FF4B44]"
      : score > 0.5
        ? "text-[#C9A84C]"
        : "text-[#8B95A8]";

  return (
    <div className="flex items-center justify-between py-3 px-4 border-b border-[#1C2333] last:border-0 hover:bg-[#1C2333]/50 transition-colors">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-[#1C2333] flex items-center justify-center text-xs font-bold text-[#8B95A8]">
          {player.name.charAt(0)}
        </div>
        <div>
          <p className="text-sm font-medium">{player.name}</p>
          <p className="text-xs text-[#8B95A8]">{player.team}</p>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-xs bg-[#1C2333] text-[#8B95A8] px-2 py-1 rounded">
          {POSITION_LABELS[player.position] ?? player.position}
        </span>
        <span className={`text-sm font-bold tabular-nums ${scoreColor}`}>
          {score.toFixed(2)}
        </span>
      </div>
    </div>
  );
}
