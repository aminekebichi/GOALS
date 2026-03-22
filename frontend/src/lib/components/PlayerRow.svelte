<script>
  import MetricBreakdown from './MetricBreakdown.svelte';

  export let player;
  export let rank;

  let expanded = false;

  const posColor = {
    ATT: '#FF4B44',
    MID: '#C9A84C',
    DEF: '#4488FF',
    GK: '#44BB88',
  };
</script>

<div class="player-row-wrapper">
  <button class="player-row" on:click={() => (expanded = !expanded)} aria-expanded={expanded}>
    <span class="rank">{rank}</span>
    <span class="name">{player.player_name}</span>
    <span class="team">{player.team_name}</span>
    <span class="pos-badge" style="color: {posColor[player.position] || '#888'}">
      {player.position}
    </span>
    <span class="score">{player.composite_score.toFixed(2)}</span>
    <span class="matches">{player.matches_played}</span>
    <span class="chevron" class:open={expanded}>›</span>
  </button>

  {#if expanded}
    <MetricBreakdown contributions={player.metric_contributions} />
  {/if}
</div>

<style>
  .player-row-wrapper {
    border-bottom: 1px solid var(--border-color);
  }

  .player-row {
    display: grid;
    grid-template-columns: 36px 1fr 140px 52px 72px 60px 24px;
    align-items: center;
    width: 100%;
    padding: 10px 16px;
    background: transparent;
    border: none;
    color: var(--text-primary);
    text-align: left;
    gap: 8px;
    cursor: pointer;
    transition: background 0.1s;
  }

  .player-row:hover {
    background: var(--bg-tertiary);
  }

  .rank {
    color: var(--text-secondary);
    font-size: 12px;
    text-align: right;
  }

  .name {
    font-weight: 600;
    font-size: 13px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .team {
    color: var(--text-secondary);
    font-size: 12px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .pos-badge {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
  }

  .score {
    font-weight: 700;
    font-size: 13px;
    color: var(--accent-primary);
    text-align: right;
  }

  .matches {
    color: var(--text-secondary);
    font-size: 12px;
    text-align: right;
  }

  .chevron {
    color: var(--text-secondary);
    font-size: 16px;
    font-weight: 300;
    text-align: center;
    transition: transform 0.2s;
    display: inline-block;
  }

  .chevron.open {
    transform: rotate(90deg);
  }
</style>
