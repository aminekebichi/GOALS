import Link from "next/link";
import Navbar from "@/components/Navbar";
import MatchCard from "@/components/MatchCard";
import UpcomingSection from "@/components/UpcomingSection";
import { prisma } from "@/lib/db";

const SEASONS = [
  { key: "2025_2026", label: "2025/26" },
  { key: "2024_2025", label: "2024/25" },
];

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ season?: string }>;
}) {
  const { season: seasonParam } = await searchParams;
  const season = SEASONS.some((s) => s.key === seasonParam)
    ? seasonParam!
    : "2025_2026";

  const raw = await prisma.match.findMany({
    where: { season },
    orderBy: { date: "desc" },
  });
  const nowIso = new Date().toISOString();
  const matches = raw.map((m) => ({ ...m, date: m.date.toISOString() }));

  // A match is "upcoming" if its kickoff date is still in the future.
  // Matches with past dates but null goals had no player data scraped.
  const upcoming = matches.filter((m) => m.date > nowIso);
  const played = matches.filter((m) => m.date <= nowIso);

  return (
    <div className="min-h-screen bg-[#0A0E1A]">
      <Navbar />
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">Match Calendar</h1>
          <p className="text-[#8B95A8]">
            Premier League match predictions powered by composite player
            performance scores
          </p>
        </div>

        {/* Season tabs */}
        <div className="flex gap-2 mb-6">
          {SEASONS.map((s) => (
            <Link
              key={s.key}
              href={`/?season=${s.key}`}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                season === s.key
                  ? "bg-[#FF4B44] text-white"
                  : "bg-[#1C2333] text-[#8B95A8] hover:text-white"
              }`}
            >
              {s.label}
            </Link>
          ))}
        </div>

        {matches.length === 0 ? (
          <div className="text-center py-20 text-[#8B95A8]">
            <p className="text-lg">No matches available</p>
            <p className="text-sm mt-2">
              Run the ML pipeline to generate predictions
            </p>
          </div>
        ) : (
          <>
            {upcoming.length > 0 && <UpcomingSection matches={upcoming} />}

            {played.length > 0 && (
              <section>
                {upcoming.length > 0 && (
                  <h2 className="text-sm font-semibold text-[#8B95A8] uppercase tracking-wider mb-3">
                    Results — {played.length} matches
                  </h2>
                )}
                <div className="grid gap-4 sm:grid-cols-2">
                  {played.map((match) => (
                    <MatchCard key={match.id} match={match} />
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
