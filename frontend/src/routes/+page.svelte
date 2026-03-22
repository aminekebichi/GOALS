<script>
  import { onMount } from 'svelte';
  import MatchCard from '$lib/components/MatchCard.svelte';

  let matches = [];
  let loading = true;
  let error = null;

  let season = '2024_2025';
  let fromRound = null;
  let toRound = null;

  async function fetchMatches() {
    loading = true;
    error = null;
    try {
      const params = new URLSearchParams({ season });
      if (fromRound) params.set('from_round', fromRound);
      if (toRound) params.set('to_round', toRound);
      const res = await fetch(`/api/matches?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      matches = data.matches;
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  onMount(fetchMatches);

  // Group matches by round
  $: grouped = matches.reduce((acc, m) => {
    const r = m.round ?? 0;
    if (!acc[r]) acc[r] = [];
    acc[r].push(m);
    return acc;
  }, {});

  $: rounds = Object.keys(grouped).map(Number).sort((a, b) => a - b);
</script>

<div class="page">
  <div class="page-header">
    <h1 class="page-title">Match Calendar</h1>
    <div class="filters">
      <label>
        Season
        <select bind:value={season} on:change={fetchMatches}>
          <option value="2024_2025">2024/25</option>
          <option value="2023_2024">2023/24</option>
          <option value="2022_2023">2022/23</option>
          <option value="2021_2022">2021/22</option>
        </select>
      </label>
      <label>
        From round
        <input type="number" min="1" max="38" bind:value={fromRound} on:change={fetchMatches} placeholder="1" />
      </label>
      <label>
        To round
        <input type="number" min="1" max="38" bind:value={toRound} on:change={fetchMatches} placeholder="38" />
      </label>
    </div>
  </div>

  {#if loading}
    <div class="state-msg">Loading matches…</div>
  {:else if error}
    <div class="state-msg error">Error: {error}</div>
  {:else if matches.length === 0}
    <div class="state-msg">No matches found. Make sure the data is scraped and the API is running.</div>
  {:else}
    {#each rounds as round}
      <div class="round-group">
        <div class="round-header">Jornada {round}</div>
        <div class="match-grid">
          {#each grouped[round] as match}
            <MatchCard {match} />
          {/each}
        </div>
      </div>
    {/each}
  {/if}
</div>

<style>
  .page {
    padding: 24px;
    max-width: 960px;
  }

  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 16px;
    margin-bottom: 24px;
  }

  .page-title {
    font-size: 22px;
    font-weight: 700;
  }

  .filters {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    align-items: flex-end;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 11px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  select, input {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 13px;
  }

  input {
    width: 70px;
  }

  select:focus, input:focus {
    outline: 1px solid var(--accent-primary);
  }

  .round-group {
    margin-bottom: 28px;
  }

  .round-header {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--text-secondary);
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border-color);
  }

  .match-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 10px;
  }

  .state-msg {
    color: var(--text-secondary);
    padding: 40px 0;
    font-size: 14px;
  }

  .state-msg.error {
    color: var(--color-win);
  }
</style>
