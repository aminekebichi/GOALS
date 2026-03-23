<script>
  import { onMount } from 'svelte';
  import MatchCard from '$lib/components/MatchCard.svelte';
  import MatchDetail from '$lib/components/MatchDetail.svelte';

  const SEASONS = [
    { id: '2025_2026', label: '2025 / 26' },
    { id: '2024_2025', label: '2024 / 25' },
    { id: '2023_2024', label: '2023 / 24' },
    { id: '2022_2023', label: '2022 / 23' },
    { id: '2021_2022', label: '2021 / 22' },
  ];

  let seasons = SEASONS.map((s, i) => ({
    ...s,
    expanded: i === 0,
    matches: [],
    loading: false,
    loaded: false,
    error: null,
  }));

  let selectedMatchId = null;
  let selectedMatchSeason = null;

  async function loadSeason(idx) {
    if (seasons[idx].loaded || seasons[idx].loading) return;
    seasons[idx] = { ...seasons[idx], loading: true };
    seasons = [...seasons];
    try {
      const res = await fetch(`/api/matches?season=${seasons[idx].id}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      // Sort: upcoming first (asc date), then past (desc date)
      const upcoming = data.matches
        .filter(m => !m.finished)
        .sort((a, b) => new Date(a.match_date) - new Date(b.match_date));
      const past = data.matches
        .filter(m => m.finished)
        .sort((a, b) => new Date(b.match_date) - new Date(a.match_date));
      seasons[idx] = { ...seasons[idx], matches: [...upcoming, ...past], loaded: true, error: null };
    } catch (e) {
      seasons[idx] = { ...seasons[idx], error: e.message };
    } finally {
      seasons[idx] = { ...seasons[idx], loading: false };
      seasons = [...seasons];
    }
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

  onMount(() => {
    // Load all seasons at once in parallel
    seasons.forEach((_, i) => loadSeason(i));
  });
</script>

<div class="page">
  {#each seasons as season, idx}
    <div class="season-section">
      <!-- Subtle season divider -->
      <button class="season-divider" on:click={() => toggleSeason(idx)}>
        <span class="divider-line" />
        <span class="divider-label">
          <span class="divider-chevron" class:open={season.expanded}>›</span>
          {season.label}
          {#if season.loaded}
            <span class="divider-count">{season.matches.length}</span>
          {:else if season.loading}
            <span class="divider-count">…</span>
          {/if}
        </span>
        <span class="divider-line" />
      </button>

      {#if season.expanded}
        <div class="match-list">
          {#if season.error}
            <div class="state-msg error">
              {season.error.includes('404') || season.error.includes('500')
                ? 'No data available for this season.'
                : season.error}
            </div>
          {:else if season.loading}
            <div class="state-msg">Loading…</div>
          {:else if season.matches.length === 0}
            <div class="state-msg">No matches found.</div>
          {:else}
            {#each season.matches as match}
              <div class="match-wrap">
                <MatchCard
                  {match}
                  selected={match.match_id === selectedMatchId}
                  on:click={() => match.finished && selectMatch(match.match_id, season.id)}
                />
                {#if match.finished && match.match_id === selectedMatchId && selectedMatchSeason === season.id}
                  <MatchDetail
                    matchId={selectedMatchId}
                    season={selectedMatchSeason}
                    homeTeam={match.home_team}
                    awayTeam={match.away_team}
                  />
                {/if}
              </div>
            {/each}
          {/if}
        </div>
      {/if}
    </div>
  {/each}
</div>

<style>
  .page {
    max-width: 860px;
    margin: 0 auto;
    padding: 32px 24px 64px;
    width: 100%;
    box-sizing: border-box;
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
