import { auth } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';
import Navbar from '@/components/Navbar';
import { prisma } from '@/lib/db';

export default async function SettingsPage() {
  const { userId } = await auth();
  if (!userId) redirect('/sign-in');

  const metrics = await prisma.pipelineMetrics.findFirst({ orderBy: { trainedAt: 'desc' } });

  return (
    <div className="min-h-screen bg-[#0A0E1A]">
      <Navbar />
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Pipeline Metrics</h1>
          <p className="text-[#8B95A8]">ML model performance on the 2024/25 test season</p>
        </div>

        {metrics ? (
          <div className="grid gap-4 sm:grid-cols-3">
            <MetricCard label="Accuracy" value={`${((metrics.accuracy ?? 0) * 100).toFixed(1)}%`} />
            <MetricCard label="Macro F1" value={(metrics.f1 ?? 0).toFixed(3)} />
            <MetricCard label="RMSE" value={(metrics.rmse ?? 0).toFixed(3)} />
            <div className="sm:col-span-3 bg-[#111827] border border-[#1C2333] rounded-xl p-5">
              <p className="text-sm text-[#8B95A8]">
                Model: <span className="text-[#F0F2F8]">{metrics.modelType}</span>
              </p>
              <p className="text-sm text-[#8B95A8] mt-1">
                Last trained:{' '}
                <span className="text-[#F0F2F8]">
                  {new Date(metrics.trainedAt).toLocaleString()}
                </span>
              </p>
            </div>
          </div>
        ) : (
          <div className="text-center py-20 text-[#8B95A8]">
            <p>No pipeline metrics found</p>
            <p className="text-sm mt-2">Run the Python ML pipeline and seed the database</p>
          </div>
        )}
      </main>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[#111827] border border-[#1C2333] rounded-xl p-6">
      <p className="text-sm text-[#8B95A8] mb-2">{label}</p>
      <p className="text-3xl font-bold text-[#FF4B44]">{value}</p>
    </div>
  );
}
