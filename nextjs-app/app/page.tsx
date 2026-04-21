import Navbar from '@/components/Navbar';
import MatchCard from '@/components/MatchCard';
import { prisma } from '@/lib/db';

export default async function HomePage() {
  const raw = await prisma.match.findMany({ orderBy: { date: 'desc' } });
  const matches = raw.map((m) => ({ ...m, date: m.date.toISOString() }));

  return (
    <div className="min-h-screen bg-[#0A0E1A]">
      <Navbar />
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Match Calendar</h1>
          <p className="text-[#8B95A8]">
            Premier League match predictions powered by composite player performance scores
          </p>
        </div>

        {matches.length === 0 ? (
          <div className="text-center py-20 text-[#8B95A8]">
            <p className="text-lg">No matches available</p>
            <p className="text-sm mt-2">Run the ML pipeline to generate predictions</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {matches.map((match) => (
              <MatchCard key={match.id} match={match} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
