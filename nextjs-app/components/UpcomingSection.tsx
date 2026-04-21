"use client";

import { useState } from "react";
import MatchCard from "@/components/MatchCard";

const INITIAL_COUNT = 5;

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

export default function UpcomingSection({ matches }: { matches: Match[] }) {
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? matches : matches.slice(0, INITIAL_COUNT);
  const hidden = matches.length - INITIAL_COUNT;

  return (
    <section className="mb-8">
      <h2 className="text-sm font-semibold text-[#8B95A8] uppercase tracking-wider mb-3">
        Upcoming — {matches.length} matches
      </h2>
      <div className="flex flex-col gap-4">
        {visible.map((match) => (
          <MatchCard key={match.id} match={match} isClickable={false} />
        ))}
      </div>
      {!showAll && hidden > 0 && (
        <button
          onClick={() => setShowAll(true)}
          className="mt-4 w-full py-2.5 rounded-xl border border-[#1C2333] text-sm text-[#8B95A8] hover:text-white hover:border-[#FF4B44]/40 transition-colors"
        >
          Show {hidden} more upcoming {hidden === 1 ? "match" : "matches"}
        </button>
      )}
    </section>
  );
}
