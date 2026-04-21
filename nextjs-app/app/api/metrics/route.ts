import { NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";

export async function GET() {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const metrics = await prisma.pipelineMetrics.findFirst({
    orderBy: { trainedAt: "desc" },
  });

  if (!metrics) {
    return NextResponse.json({ error: "No metrics found" }, { status: 404 });
  }

  return NextResponse.json({
    accuracy: metrics.accuracy,
    f1: metrics.f1,
    rmse: metrics.rmse,
    trainedAt: metrics.trainedAt,
    modelType: metrics.modelType,
  });
}
