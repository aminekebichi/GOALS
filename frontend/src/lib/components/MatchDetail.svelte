<script>
  import { onMount } from 'svelte';

  export let matchId;
  export let season;
  export let leagueId = 47;
  export let homeTeam;
  export let awayTeam;

  let players = [];
  let motm = null;
  let loading = true;
  let error = null;
  let noData = false;

  let selectedPlayerId = null;

  const posColor = { ATT: '#FF4B44', MID: '#C9A84C', DEF: '#4488FF', GK: '#44BB88' };
  const posOrder = { GK: 0, DEF: 1, MID: 2, ATT: 3 };

  onMount(async () => {
    try {
      const res = await fetch(`/api/matches/${matchId}/players?season=${season}&league_id=${leagueId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      players = data.players;
      motm = data.motm;
      noData = players.length === 0;
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  $: homePlayers = players
    .filter(p => p.team_name === homeTeam)
    .sort((a, b) => (posOrder[a.position] ?? 9) - (posOrder[b.position] ?? 9) || b.composite_score - a.composite_score);

  $: awayPlayers = players
    .filter(p => p.team_name !== homeTeam)
    .sort((a, b) => (posOrder[a.position] ?? 9) - (posOrder[b.position] ?? 9) || b.composite_score - a.composite_score);

  $: maxScore = Math.max(...players.map(p => Math.abs(p.composite_score)), 0.001);

  function togglePlayer(id) {
    selectedPlayerId = selectedPlayerId === id ? null : id;
  }

  // For contribution bars: max absolute contribution value across all metrics
  function maxContrib(contributions) {
    const vals = Object.values(contributions).map(Math.abs);
    return Math.max(...vals, 0.001);
  }
</script>

<div class="detail">
  {#if loading}
    <div class="state">Loading player data…</div>
  {:else if error}
    <div class="state error">Failed to load: {error}</div>
  {:else if noData}
    <div class="state muted">
      Player performance data is not available for this match.
      Run <code>fotmob_final.ipynb</code> to collect match data.
    </div>
  {:else}
    {#if motm}
      <div class="motm-banner">
        <span class="motm-crown">★</span>
        <span class="motm-label">Man of the Match</span>
        <span class="motm-name">{motm.player_name}</span>
        <span class="motm-team">({motm.team_name})</span>
        <span class="motm-score">{motm.composite_score.toFixed(2)}</span>
      </div>
    {/if}

    <div class="teams-grid">
      <!-- Home team -->
      <div class="team-col">
        <div class="team-header">{homeTeam}</div>
        {#each homePlayers as player}
          <div
            class="player-row"
            class:motm={player.is_motm}
            class:expanded={selectedPlayerId === player.player_id}
            role="button"
            tabindex="0"
            on:click={() => togglePlayer(player.player_id)}
            on:keydown={e => e.key === 'Enter' && togglePlayer(player.player_id)}
          >
            <span class="pos" style="color: {posColor[player.position] || '#888'}">{player.position}</span>
            <span class="pname" class:motm-name-highlight={player.is_motm}>
              {player.player_name}
              {#if player.is_motm}<span class="star">★</span>{/if}
            </span>
            <div class="score-bar-wrap">
              <div
                class="score-bar"
                style="width: {Math.abs(player.composite_score) / maxScore * 100}%; background: {posColor[player.position] || '#888'}"
              />
            </div>
            <span class="score">{player.composite_score.toFixed(2)}</span>
          </div>

          {#if selectedPlayerId === player.player_id}
            <div class="player-detail" style="--pos-color: {posColor[player.position] || '#888'}">
              <div class="pd-header">
                <span class="pd-name">{player.player_name}</span>
                <span class="pd-pos" style="color: {posColor[player.position]}">{player.position}</span>
                <span class="pd-score">{player.composite_score.toFixed(3)}</span>
              </div>

              <!-- Score contributions (weighted z-scores) -->
              <div class="pd-section-label">Score Contributions</div>
              <div class="pd-contributions">
                {#each Object.entries(player.metric_contributions).sort((a,b) => Math.abs(b[1]) - Math.abs(a[1])) as [key, val]}
                  {@const mc = maxContrib(player.metric_contributions)}
                  <div class="pd-contrib-row">
                    <span class="pd-contrib-label">{key.replace(/_/g, ' ')}</span>
                    <div class="pd-contrib-bar-wrap">
                      <div
                        class="pd-contrib-bar"
                        class:negative={val < 0}
                        style="width: {Math.abs(val) / mc * 100}%"
                      />
                    </div>
                    <span class="pd-contrib-val" class:negative={val < 0}>{val > 0 ? '+' : ''}{val.toFixed(3)}</span>
                  </div>
                {/each}
              </div>

              <!-- Raw stats -->
              <div class="pd-section-label" style="margin-top: 12px">Raw Stats</div>
              <div class="pd-raw-grid">
                {#each Object.entries(player.raw_stats) as [label, val]}
                  <div class="pd-raw-item">
                    <span class="pd-raw-label">{label}</span>
                    <span class="pd-raw-val">{typeof val === 'number' ? (Number.isInteger(val) ? val : val.toFixed(2)) : val}</span>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        {/each}
      </div>

      <div class="divider" />

      <!-- Away team -->
      <div class="team-col">
        <div class="team-header">{awayTeam}</div>
        {#each awayPlayers as player}
          <div
            class="player-row"
            class:motm={player.is_motm}
            class:expanded={selectedPlayerId === player.player_id}
            role="button"
            tabindex="0"
            on:click={() => togglePlayer(player.player_id)}
            on:keydown={e => e.key === 'Enter' && togglePlayer(player.player_id)}
          >
            <span class="pos" style="color: {posColor[player.position] || '#888'}">{player.position}</span>
            <span class="pname" class:motm-name-highlight={player.is_motm}>
              {player.player_name}
              {#if player.is_motm}<span class="star">★</span>{/if}
            </span>
            <div class="score-bar-wrap">
              <div
                class="score-bar"
                style="width: {Math.abs(player.composite_score) / maxScore * 100}%; background: {posColor[player.position] || '#888'}"
              />
            </div>
            <span class="score">{player.composite_score.toFixed(2)}</span>
          </div>

          {#if selectedPlayerId === player.player_id}
            <div class="player-detail" style="--pos-color: {posColor[player.position] || '#888'}">
              <div class="pd-header">
                <span class="pd-name">{player.player_name}</span>
                <span class="pd-pos" style="color: {posColor[player.position]}">{player.position}</span>
                <span class="pd-score">{player.composite_score.toFixed(3)}</span>
              </div>

              <div class="pd-section-label">Score Contributions</div>
              <div class="pd-contributions">
                {#each Object.entries(player.metric_contributions).sort((a,b) => Math.abs(b[1]) - Math.abs(a[1])) as [key, val]}
                  {@const mc = maxContrib(player.metric_contributions)}
                  <div class="pd-contrib-row">
                    <span class="pd-contrib-label">{key.replace(/_/g, ' ')}</span>
                    <div class="pd-contrib-bar-wrap">
                      <div
                        class="pd-contrib-bar"
                        class:negative={val < 0}
                        style="width: {Math.abs(val) / mc * 100}%"
                      />
                    </div>
                    <span class="pd-contrib-val" class:negative={val < 0}>{val > 0 ? '+' : ''}{val.toFixed(3)}</span>
                  </div>
                {/each}
              </div>

              <div class="pd-section-label" style="margin-top: 12px">Raw Stats</div>
              <div class="pd-raw-grid">
                {#each Object.entries(player.raw_stats) as [label, val]}
                  <div class="pd-raw-item">
                    <span class="pd-raw-label">{label}</span>
                    <span class="pd-raw-val">{typeof val === 'number' ? (Number.isInteger(val) ? val : val.toFixed(2)) : val}</span>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .detail {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    border-radius: 0 0 6px 6px;
    padding: 16px;
    animation: slideDown 0.2s ease;
    margin-left: -12px;
    margin-right: -12px;
  }

  @keyframes slideDown {
    from { opacity: 0; transform: translateY(-6px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .state { padding: 12px 0; font-size: 13px; color: var(--text-primary); }
  .state.muted { color: var(--text-secondary); line-height: 1.6; }
  .state.error { color: var(--color-win); }
  .state code {
    background: var(--bg-tertiary);
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 11px;
    color: var(--accent-secondary);
  }

  /* MOTM banner */
  .motm-banner {
    display: flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(90deg, rgba(255,75,68,0.12), transparent);
    border-left: 3px solid var(--accent-primary);
    border-radius: 4px;
    padding: 8px 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }
  .motm-crown { color: #FFD700; font-size: 16px; }
  .motm-label { font-size: 10px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: var(--text-secondary); }
  .motm-name { font-weight: 700; font-size: 14px; color: var(--text-primary); }
  .motm-team { font-size: 12px; color: var(--text-secondary); }
  .motm-score { margin-left: auto; font-weight: 700; font-size: 14px; color: var(--accent-primary); }

  /* Two-column layout */
  .teams-grid {
    display: grid;
    grid-template-columns: 1fr 1px 1fr;
    gap: 0 20px;
  }
  .divider { background: var(--border-color); width: 1px; }

  .team-header {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--text-secondary);
    padding-bottom: 8px;
    margin-bottom: 6px;
    border-bottom: 1px solid var(--border-color);
  }

  /* Player rows */
  .player-row {
    display: grid;
    grid-template-columns: 32px 1fr 60px 40px;
    align-items: center;
    gap: 6px;
    padding: 5px 6px;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.1s;
  }
  .player-row:hover { background: var(--bg-tertiary); }
  .player-row.motm { background: rgba(255, 75, 68, 0.06); }
  .player-row.expanded { background: var(--bg-tertiary); border-radius: 4px 4px 0 0; }

  .pos { font-size: 10px; font-weight: 700; letter-spacing: 0.5px; }

  .pname {
    font-size: 12px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .motm-name-highlight { font-weight: 700; color: var(--text-primary); }
  .star { color: #FFD700; font-size: 11px; flex-shrink: 0; }

  .score-bar-wrap { height: 4px; background: var(--bg-tertiary); border-radius: 2px; overflow: hidden; }
  .score-bar { height: 100%; border-radius: 2px; transition: width 0.3s ease; }

  .score { font-size: 11px; font-weight: 600; color: var(--text-primary); text-align: right; }

  /* ── Player detail panel ── */
  .player-detail {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-top: 2px solid var(--pos-color);
    border-radius: 0 0 6px 6px;
    padding: 12px 14px;
    margin-bottom: 4px;
    animation: slideDown 0.15s ease;
  }

  .pd-header {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin-bottom: 12px;
  }
  .pd-name { font-weight: 700; font-size: 13px; flex: 1; }
  .pd-pos { font-size: 10px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; }
  .pd-score { font-size: 13px; font-weight: 700; color: var(--accent-primary); }

  .pd-section-label {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--text-secondary);
    margin-bottom: 6px;
  }

  /* Contribution bars */
  .pd-contributions { display: flex; flex-direction: column; gap: 4px; }

  .pd-contrib-row {
    display: grid;
    grid-template-columns: 110px 1fr 52px;
    align-items: center;
    gap: 8px;
  }

  .pd-contrib-label {
    font-size: 11px;
    color: var(--text-secondary);
    text-transform: capitalize;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .pd-contrib-bar-wrap {
    height: 6px;
    background: var(--bg-tertiary);
    border-radius: 3px;
    overflow: hidden;
  }

  .pd-contrib-bar {
    height: 100%;
    border-radius: 3px;
    background: var(--pos-color);
    transition: width 0.3s ease;
  }

  .pd-contrib-bar.negative { background: var(--text-secondary); opacity: 0.5; }

  .pd-contrib-val {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-primary);
    text-align: right;
  }
  .pd-contrib-val.negative { color: var(--text-secondary); }

  /* Raw stats grid */
  .pd-raw-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 4px 12px;
  }

  .pd-raw-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 6px;
    background: var(--bg-secondary);
    border-radius: 4px;
    gap: 8px;
  }

  .pd-raw-label {
    font-size: 11px;
    color: var(--text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .pd-raw-val {
    font-size: 12px;
    font-weight: 700;
    color: var(--text-primary);
    flex-shrink: 0;
  }
</style>
