from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from goals_app.routers import calendar, stats

app = FastAPI(title="GOALS — Game Outcome and Analytics Learning System")

# Register API routers
app.include_router(calendar.router, prefix="/api")
app.include_router(stats.router, prefix="/api")


# ---------------------------------------------------------------------------
# Serve compiled Svelte SPA for all non-API routes
# ---------------------------------------------------------------------------

DIST = Path(__file__).parent.parent / "frontend" / "dist"

if DIST.exists():
    # Mount every top-level subdirectory in dist as a static path
    for subdir in DIST.iterdir():
        if subdir.is_dir():
            app.mount(f"/{subdir.name}", StaticFiles(directory=str(subdir)), name=subdir.name)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        index = DIST / "index.html"
        return FileResponse(str(index))
