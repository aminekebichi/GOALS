import Navbar from '@/components/Navbar';
import MatchCard from '@/components/MatchCard';

async function getMatches() {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_APP_URL ?? 'http://localhost:3000'}/api/matches`, {
      cache: 'no-store',
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.matches ?? [];
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const matches = await getMatches();

  return (
    <div className="min-h-screen bg-[#0A0E1A]">
      <Navbar />
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Match Calendar</h1>
          <p className="text-[#8B95A8]">
            La Liga match predictions powered by composite player performance scores
          </p>
        </div>

        {matches.length === 0 ? (
          <div className="text-center py-20 text-[#8B95A8]">
            <p className="text-lg">No matches available</p>
            <p className="text-sm mt-2">Run the ML pipeline to generate predictions</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {matches.map((match: Parameters<typeof MatchCard>[0]['match']) => (
              <MatchCard key={match.id} match={match} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
