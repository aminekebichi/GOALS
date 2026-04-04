from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from goals_app.routers import calendar, stats
from goals_app.config import LEAGUE_MAP, DEFAULT_LEAGUE_ID, FOTMOB_DIRS

app = FastAPI(title="GOALS — Game Outcome and Analytics Learning System")

# Register API routers
app.include_router(calendar.router, prefix="/api")
app.include_router(stats.router, prefix="/api")


@app.get("/api/leagues")
async def get_leagues():
    """Return all supported leagues and their available seasons."""
    result = []
    for league_id, meta in LEAGUE_MAP.items():
        fotmob_dir = FOTMOB_DIRS[league_id]
        seasons = []
        if fotmob_dir.exists():
            for season_dir in sorted(fotmob_dir.iterdir()):
                if season_dir.is_dir():
                    has_players = (season_dir / "output" / "outfield_players.parquet").exists()
                    has_fixtures = (season_dir / "output" / "fixtures.parquet").exists()
                    if has_fixtures:
                        seasons.append({
                            "season": season_dir.name,
                            "has_player_data": has_players,
                        })
        result.append({
            "league_id": league_id,
            "name": meta["name"],
            "slug": meta["slug"],
            "is_default": league_id == DEFAULT_LEAGUE_ID,
            "seasons": seasons,
        })
    return {"leagues": result}


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
