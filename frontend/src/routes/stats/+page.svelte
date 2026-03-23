<script>
  import { onMount } from 'svelte';
  import PlayerRow from '$lib/components/PlayerRow.svelte';

  let players = [];
  let loading = true;
  let error = null;

  let season = '2025_2026';
  let position = 'all';
  let searchInput = '';

  const positions = ['all', 'ATT', 'MID', 'DEF', 'GK'];

  async function fetchPlayers() {
    loading = true;
    error = null;
    try {
      const params = new URLSearchParams({ season, position });
      const res = await fetch(`/api/players?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      players = data.players;
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  onMount(fetchPlayers);

  // Client-side search filter
  $: filtered = searchInput.trim()
    ? players.filter(p =>
        p.player_name.toLowerCase().includes(searchInput.toLowerCase()) ||
        p.team_name.toLowerCase().includes(searchInput.toLowerCase())
      )
    : players;
</script>

<div class="page">
  <div class="page-header">
    <h1 class="page-title">Player Stats</h1>
    <div class="filters">
      <label>
        Season
        <select bind:value={season} on:change={fetchPlayers}>
          <option value="2025_2026">2025/26</option>
          <option value="2024_2025">2024/25</option>
          <option value="2023_2024">2023/24</option>
          <option value="2022_2023">2022/23</option>
          <option value="2021_2022">2021/22</option>
        </select>
      </label>
      <label>
        Search
        <input
          type="text"
          bind:value={searchInput}
          placeholder="Player or team…"
          style="width: 160px"
        />
      </label>
    </div>
  </div>

  <!-- Position tabs -->
  <div class="pos-tabs">
    {#each positions as pos}
      <button
        class="pos-tab"
        class:active={position === pos}
        on:click={() => { position = pos; fetchPlayers(); }}
      >
        {pos === 'all' ? 'ALL' : pos}
      </button>
    {/each}
  </div>

  <!-- Table -->
  {#if loading}
    <div class="state-msg">Loading players…</div>
  {:else if error}
    <div class="state-msg error">Error: {error}</div>
  {:else if filtered.length === 0}
    <div class="state-msg">No players found.</div>
  {:else}
    <div class="table-container">
      <div class="table-header">
        <span class="col-rank">#</span>
        <span class="col-name">Player</span>
        <span class="col-team">Team</span>
        <span class="col-pos">Pos</span>
        <span class="col-score">Score</span>
        <span class="col-matches">MP</span>
        <span class="col-expand"></span>
      </div>
      <div class="table-body">
        {#each filtered as player, i}
          <PlayerRow {player} rank={i + 1} />
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .page {
    padding: 24px;
    width: 100%;
    box-sizing: border-box;
  }

  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 16px;
    margin-bottom: 20px;
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

  select:focus, input:focus {
    outline: 1px solid var(--accent-primary);
  }

  .pos-tabs {
    display: flex;
    gap: 4px;
    margin-bottom: 16px;
  }

  .pos-tab {
    padding: 6px 16px;
    border-radius: 20px;
    border: 1px solid var(--border-color);
    background: transparent;
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
    transition: all 0.15s;
  }

  .pos-tab:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
  }

  .pos-tab.active {
    background: var(--accent-primary);
    border-color: var(--accent-primary);
    color: white;
  }

  .table-container {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    overflow: hidden;
  }

  .table-header {
    display: grid;
    grid-template-columns: 36px 1fr 140px 52px 72px 60px 24px;
    gap: 8px;
    padding: 8px 16px;
    background: var(--bg-tertiary);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--text-secondary);
    border-bottom: 1px solid var(--border-color);
  }

  .col-rank { text-align: right; }
  .col-score { text-align: right; }
  .col-matches { text-align: right; }

  .state-msg {
    color: var(--text-secondary);
    padding: 40px 0;
    font-size: 14px;
  }

  .state-msg.error {
    color: var(--color-win);
  }
</style>
