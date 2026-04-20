import { auth } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';
import Navbar from '@/components/Navbar';
import PlayerRow from '@/components/PlayerRow';

async function getPlayers(searchParams: { position?: string; team?: string }) {
  const params = new URLSearchParams();
  if (searchParams.position) params.set('position', searchParams.position);
  if (searchParams.team) params.set('team', searchParams.team);

  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_APP_URL ?? 'http://localhost:3000'}/api/players?${params}`,
      { cache: 'no-store' }
    );
    if (!res.ok) return [];
    const data = await res.json();
    return data.players ?? [];
  } catch {
    return [];
  }
}

const POSITIONS = ['ATT', 'MID', 'DEF', 'GK'];

export default async function StatsPage({
  searchParams,
}: {
  searchParams: Promise<{ position?: string; team?: string }>;
}) {
  const { userId } = await auth();
  if (!userId) redirect('/sign-in');

  const params = await searchParams;
  const players = await getPlayers(params);

  return (
    <div className="min-h-screen bg-[#0A0E1A]">
      <Navbar />
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Player Stats</h1>
          <p className="text-[#8B95A8]">Composite performance scores by position</p>
        </div>

        <div className="flex gap-2 mb-6 flex-wrap">
          {POSITIONS.map((pos) => (
            <a
              key={pos}
              href={`/stats?position=${pos}`}
              className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                params.position === pos
                  ? 'bg-[#FF4B44] text-white'
                  : 'bg-[#1C2333] text-[#8B95A8] hover:text-white'
              }`}
            >
              {pos}
            </a>
          ))}
          {params.position && (
            <a href="/stats" className="px-3 py-1 rounded-lg text-sm bg-[#1C2333] text-[#8B95A8] hover:text-white">
              Clear
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
