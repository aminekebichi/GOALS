import { auth } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';
import Navbar from '@/components/Navbar';
import PlayerRow from '@/components/PlayerRow';
import { prisma } from '@/lib/db';

const POSITIONS: { label: string; value: string }[] = [
  { label: 'Forwards', value: 'forward' },
  { label: 'Midfielders', value: 'midfielder' },
  { label: 'Defenders', value: 'defender' },
  { label: 'Goalkeepers', value: 'goalkeeper' },
];

export default async function StatsPage({
  searchParams,
}: {
  searchParams: Promise<{ position?: string; team?: string }>;
}) {
  const { userId } = await auth();
  if (!userId) redirect('/sign-in');

  const params = await searchParams;
  const where: Record<string, string> = { season: '2024_2025' };
  if (params.position) where.position = params.position;
  if (params.team) where.team = params.team;
  const players = await prisma.player.findMany({ where, orderBy: { name: 'asc' } });

  return (
    <div className="min-h-screen bg-[#0A0E1A]">
      <Navbar />
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Player Stats</h1>
          <p className="text-[#8B95A8]">Premier League composite performance scores by position — 2024/25 season</p>
        </div>

        <div className="flex gap-2 mb-6 flex-wrap">
          {POSITIONS.map(({ label, value }) => (
            <a
              key={value}
              href={`/stats?position=${value}`}
              className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                params.position === value
                  ? 'bg-[#FF4B44] text-white'
                  : 'bg-[#1C2333] text-[#8B95A8] hover:text-white'
              }`}
            >
              {label}
            </a>
          ))}
          {params.position && (
            <a href="/stats" className="px-3 py-1 rounded-lg text-sm bg-[#1C2333] text-[#8B95A8] hover:text-white">
              All
            </a>
          )}
        </div>

        <div className="bg-[#111827] border border-[#1C2333] rounded-xl overflow-hidden">
          {players.length === 0 ? (
            <div className="text-center py-16 text-[#8B95A8]">No players found</div>
          ) : (
            players.map((player: Parameters<typeof PlayerRow>[0]['player']) => (
              <PlayerRow key={player.id} player={player} />
            ))
          )}
        </div>
      </main>
    </div>
  );
}
