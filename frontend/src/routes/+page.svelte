<script>
  import { onMount } from 'svelte';
  import MatchCard from '$lib/components/MatchCard.svelte';
  import MatchDetail from '$lib/components/MatchDetail.svelte';

  const PAGE_SIZE = 5;

  const LEAGUE_CONFIG = {
    47: {
      name: 'Premier League',
      seasons: [
        { id: '2025_2026', label: '2025 / 26' },
        { id: '2024_2025', label: '2024 / 25' },
        { id: '2023_2024', label: '2023 / 24' },
        { id: '2022_2023', label: '2022 / 23' },
        { id: '2021_2022', label: '2021 / 22' },
      ],
    },
    87: {
      name: 'La Liga',
      seasons: [
        { id: '2025_2026', label: '2025 / 26' },
        { id: '2024_2025', label: '2024 / 25' },
        { id: '2023_2024', label: '2023 / 24' },
        { id: '2022_2023', label: '2022 / 23' },
        { id: '2021_2022', label: '2021 / 22' },
      ],
    },
  };

  let leagueId = 47;

  function makeSeasonState(seasonList) {
    return seasonList.map((s, i) => ({
      ...s,
      expanded: i === 0,
      upcomingMatches: [],
      pastMatches: [],
      visibleCount: PAGE_SIZE,
      loading: false,
      loaded: false,
      error: null,
      predictionsLoading: false,
      predictionsLoaded: false,
    }));
  }

  let seasons = makeSeasonState(LEAGUE_CONFIG[leagueId].seasons);

  let selectedMatchId = null;
  let selectedMatchSeason = null;

  async function loadSeason(idx) {
    if (seasons[idx].loaded || seasons[idx].loading) return;
    seasons[idx] = { ...seasons[idx], loading: true };
    seasons = [...seasons];
    try {
      const res = await fetch(`/api/matches?season=${seasons[idx].id}&league_id=${leagueId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const upcoming = data.matches
        .filter(m => !m.finished)
        .sort((a, b) => new Date(a.match_date) - new Date(b.match_date));
      const past = data.matches
        .filter(m => m.finished)
        .sort((a, b) => new Date(b.match_date) - new Date(a.match_date));
      seasons[idx] = {
        ...seasons[idx],
        upcomingMatches: upcoming,
        pastMatches: past,
        loaded: true,
        error: null,
      };
    } catch (e) {
      seasons[idx] = { ...seasons[idx], error: e.message };
    } finally {
      seasons[idx] = { ...seasons[idx], loading: false };
      seasons = [...seasons];
    }
    loadPredictions(idx);
  }

  async function loadPredictions(idx) {
    if (seasons[idx].predictionsLoaded || seasons[idx].predictionsLoading) return;
    seasons[idx] = { ...seasons[idx], predictionsLoading: true };
    seasons = [...seasons];
    try {
      const res = await fetch(`/api/predictions?season=${seasons[idx].id}&league_id=${leagueId}`);
      if (!res.ok) return;
      const data = await res.json();
      const predMap = {};
      for (const p of data.predictions) predMap[p.match_id] = p;
      const patch = m => ({ ...m, prediction: predMap[m.match_id] ?? m.prediction ?? null });
      seasons[idx] = {
        ...seasons[idx],
        upcomingMatches: seasons[idx].upcomingMatches.map(patch),
        pastMatches: seasons[idx].pastMatches.map(patch),
        predictionsLoaded: true,
      };
    } catch (_) {
      // Predictions are best-effort — silently ignore errors
    } finally {
      seasons[idx] = { ...seasons[idx], predictionsLoading: false };
      seasons = [...seasons];
    }
  }

  function showMore(idx) {
    seasons[idx] = { ...seasons[idx], visibleCount: seasons[idx].visibleCount + PAGE_SIZE };
    seasons = [...seasons];
  }

  function toggleSeason(idx) {
    seasons[idx] = { ...seasons[idx], expanded: !seasons[idx].expanded };
    seasons = [...seasons];
    if (seasons[idx].expanded && !seasons[idx].loaded) {
      loadSeason(idx);
    }
  }

  function selectMatch(matchId, seasonId) {
    if (selectedMatchId === matchId) {
      selectedMatchId = null;
      selectedMatchSeason = null;
    } else {
      selectedMatchId = matchId;
      selectedMatchSeason = seasonId;
    }
  }

  function switchLeague(id) {
    if (id === leagueId) return;
    leagueId = id;
    selectedMatchId = null;
    selectedMatchSeason = null;
    seasons = makeSeasonState(LEAGUE_CONFIG[id].seasons);
    seasons.forEach((_, i) => loadSeason(i));
  }

  onMount(() => {
    seasons.forEach((_, i) => loadSeason(i));
  });
</script>

<div class="page">
  <!-- League toggle -->
  <div class="league-toggle">
    {#each Object.entries(LEAGUE_CONFIG) as [id, cfg]}
      <button
        class="league-btn"
        class:active={leagueId === Number(id)}
        on:click={() => switchLeague(Number(id))}
      >
        {cfg.name}
      </button>
    {/each}
  </div>

  {#each seasons as season, idx}
    <div class="season-section">
      <button class="season-divider" on:click={() => toggleSeason(idx)}>
        <span class="divider-line" />
        <span class="divider-label">
          <span class="divider-chevron" class:open={season.expanded}>›</span>
          {season.label}
          {#if season.loaded}
            <span class="divider-count">{season.upcomingMatches.length + season.pastMatches.length}</span>
          {:else if season.loading}
            <span class="divider-count">…</span>
          {/if}
        </span>
        <span class="divider-line" />
      </button>

      {#if season.expanded}
        {#if season.predictionsLoading}
          <div class="predictions-bar">
            <div class="predictions-bar-fill" />
            <span class="predictions-bar-label">Computing predictions…</span>
          </div>
        {/if}

        {#if season.error}
          <div class="state-msg error">
            {season.error.includes('404') || season.error.includes('500')
              ? 'No data available for this season.'
              : season.error}
          </div>
        {:else if season.loading}
          <div class="state-msg">Loading…</div>
        {:else if season.upcomingMatches.length === 0 && season.pastMatches.length === 0}
          <div class="state-msg">No matches found.</div>
        {:else}

          <!-- Upcoming fixtures -->
          {#if season.upcomingMatches.length > 0}
            <div class="subsection-header">Upcoming</div>
            <div class="match-list">
              {#each season.upcomingMatches as match}
                <div class="match-wrap">
                  <MatchCard
                    {match}
                    selected={false}
                    on:click={() => {}}
                  />
                </div>
              {/each}
            </div>

            {#if season.pastMatches.length > 0}
              <div class="subsection-header past-header">Results</div>
            {/if}
          {/if}

          <!-- Past matches (paginated) -->
          {#if season.pastMatches.length > 0}
            <div class="match-list">
              {#each season.pastMatches.slice(0, season.visibleCount) as match}
                <div class="match-wrap">
                  <MatchCard
                    {match}
                    selected={match.match_id === selectedMatchId}
                    on:click={() => selectMatch(match.match_id, season.id)}
                  />
                  {#if match.match_id === selectedMatchId && selectedMatchSeason === season.id}
                    <MatchDetail
                      matchId={selectedMatchId}
                      season={selectedMatchSeason}
                      {leagueId}
                      homeTeam={match.home_team}
                      awayTeam={match.away_team}
                    />
                  {/if}
                </div>
              {/each}
            </div>

            {#if season.visibleCount < season.pastMatches.length}
              <button class="show-more" on:click={() => showMore(idx)}>
                Show {Math.min(PAGE_SIZE, season.pastMatches.length - season.visibleCount)} more
                <span class="show-more-total">({season.pastMatches.length - season.visibleCount} remaining)</span>
              </button>
            {/if}
          {/if}

        {/if}
      {/if}
    </div>
  {/each}
</div>

<style>
  .page {
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;
    padding: 32px 48px 64px;
    box-sizing: border-box;
  }

  @media (max-width: 768px) {
    .page {
      padding: 20px 16px 48px;
    }
  }

  /* League toggle */
  .league-toggle {
    display: flex;
    gap: 8px;
    margin-bottom: 28px;
  }

  .league-btn {
    padding: 7px 18px;
    border-radius: 20px;
    border: 1px solid var(--border-color);
    background: transparent;
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
    cursor: pointer;
    transition: all 0.15s;
  }

  .league-btn:hover {
    border-color: var(--accent-primary);
    color: var(--text-primary);
  }

  .league-btn.active {
    background: var(--accent-primary);
    border-color: var(--accent-primary);
    color: #fff;
  }

  /* Season divider */
  .season-section {
    margin-bottom: 8px;
  }

  .season-divider {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 12px;
    background: none;
    border: none;
    cursor: pointer;
    padding: 10px 0;
    color: var(--text-secondary);
  }

  .season-divider:hover .divider-label {
    color: var(--text-primary);
  }

  .divider-line {
    flex: 1;
    height: 1px;
    background: var(--border-color);
  }

  .divider-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    white-space: nowrap;
    transition: color 0.15s;
  }

  .divider-chevron {
    font-size: 14px;
    font-weight: 300;
    transition: transform 0.2s;
    display: inline-block;
    line-height: 1;
  }

  .divider-chevron.open {
    transform: rotate(90deg);
  }

  .divider-count {
    font-size: 10px;
    font-weight: 400;
    opacity: 0.6;
  }

  /* Predictions loading bar */
  .predictions-bar {
    position: relative;
    height: 2px;
    background: var(--bg-tertiary);
    margin-bottom: 12px;
    overflow: hidden;
    border-radius: 1px;
  }

  .predictions-bar-fill {
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
    animation: slide 1.4s ease-in-out infinite;
    transform-origin: left;
  }

  @keyframes slide {
    0%   { transform: translateX(-100%); }
    50%  { transform: translateX(0%); }
    100% { transform: translateX(100%); }
  }

  .predictions-bar-label {
    position: absolute;
    top: 6px;
    right: 0;
    font-size: 10px;
    color: var(--text-secondary);
    letter-spacing: 0.5px;
  }

  /* Subsection headers (Upcoming / Results) */
  .subsection-header {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--accent-primary);
    padding: 10px 0 6px;
  }

  .past-header {
    color: var(--text-secondary);
    margin-top: 8px;
  }

  /* Match list */
  .match-list {
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .match-wrap {
    display: flex;
    flex-direction: column;
  }

  /* Show more */
  .show-more {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 12px 0;
    background: none;
    border: none;
    border-top: 1px solid var(--border-color);
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
    cursor: pointer;
    transition: color 0.15s;
    text-align: left;
  }

  .show-more:hover {
    color: var(--accent-primary);
  }

  .show-more-total {
    font-weight: 400;
    opacity: 0.6;
  }

  .state-msg {
    color: var(--text-secondary);
    padding: 16px 0;
    font-size: 13px;
    text-align: center;
  }

  .state-msg.error {
    color: var(--accent-secondary);
  }
</style>
