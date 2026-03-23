<script>
  import { createEventDispatcher } from 'svelte';
  import ProbabilityBar from './ProbabilityBar.svelte';

  export let match;
  export let selected = false;

  const dispatch = createEventDispatcher();

  function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
  }
</script>

<div
  class="match-card"
  class:finished={match.finished}
  class:upcoming={!match.finished}
  class:selected
  role="button"
  tabindex="0"
  on:click
  on:keydown={e => e.key === 'Enter' && dispatch('click')}
>
  <div class="card-inner">
    <!-- Left: team names + date -->
    <div class="match-info">
      <div class="teams">
        <span class="team home">{match.home_team}</span>
        <span class="vs">vs</span>
        <span class="team away">{match.away_team}</span>
      </div>
      <div class="meta-row">
        <span class="date">{formatDate(match.match_date)}</span>
        {#if match.round != null}
          <span class="round-badge">MD {match.round}</span>
        {/if}
        {#if match.finished && match.home_score !== null}
          <span class="score-badge">{match.home_score} – {match.away_score}</span>
        {/if}
      </div>
    </div>

    <!-- Right: probability bars -->
    <div class="prediction">
      {#if match.prediction}
        <ProbabilityBar
          label={match.home_team}
          probability={match.prediction.win_prob}
          color="var(--color-win)"
        />
        <ProbabilityBar
          label="Draw"
          probability={match.prediction.draw_prob}
          color="var(--color-draw)"
        />
        <ProbabilityBar
          label={match.away_team}
          probability={match.prediction.loss_prob}
          color="var(--color-loss)"
        />
      {:else}
        <div class="no-pred">No prediction available</div>
      {/if}
    </div>
  </div>

  {#if match.finished}
    {#if selected}
      <div class="expand-hint">▲ hide</div>
    {:else}
      <div class="expand-hint">▼ player stats</div>
    {/if}
  {/if}
</div>

<style>
  .match-card {
    border-bottom: 1px solid var(--border-color);
    padding: 16px 0;
    transition: background 0.15s;
    position: relative;
  }

  .match-card.finished {
    cursor: pointer;
    opacity: 0.55;
  }

  .match-card.upcoming {
    cursor: default;
  }

  .match-card.finished:hover,
  .match-card.selected.finished {
    opacity: 1;
  }

  .match-card:hover,
  .match-card.selected {
    background: var(--bg-secondary);
    padding-left: 12px;
    padding-right: 12px;
    margin-left: -12px;
    margin-right: -12px;
    border-radius: 6px;
  }

  .match-card.selected {
    border-bottom-left-radius: 0;
    border-bottom-right-radius: 0;
    border-bottom-color: transparent;
  }

  .match-card.upcoming {
    border-left: 2px solid var(--accent-primary);
    padding-left: 14px;
  }

  .match-card.upcoming:hover,
  .match-card.upcoming.selected {
    padding-left: 26px;
    margin-left: -12px;
  }

  .card-inner {
    display: flex;
    align-items: center;
    gap: 24px;
  }

  /* Match info: left side */
  .match-info {
    flex: 1;
    min-width: 0;
  }

  .teams {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
    flex-wrap: wrap;
  }

  .team {
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 200px;
  }

  .vs {
    font-size: 11px;
    color: var(--text-secondary);
    font-weight: 400;
    flex-shrink: 0;
  }

  .meta-row {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .date {
    font-size: 12px;
    color: var(--text-secondary);
  }

  .round-badge {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    background: var(--bg-tertiary);
    padding: 2px 6px;
    border-radius: 3px;
  }

  .score-badge {
    font-size: 13px;
    font-weight: 700;
    color: var(--text-primary);
    background: var(--bg-tertiary);
    padding: 3px 10px;
    border-radius: 4px;
    letter-spacing: 1px;
  }

  /* Prediction bars: right side */
  .prediction {
    width: 340px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .no-pred {
    font-size: 11px;
    color: var(--text-secondary);
    text-align: right;
  }

  /* Expand hint */
  .expand-hint {
    font-size: 10px;
    color: var(--text-secondary);
    letter-spacing: 0.5px;
    text-align: right;
    margin-top: 8px;
    opacity: 0.5;
  }

  .match-card:hover .expand-hint,
  .match-card.selected .expand-hint {
    opacity: 1;
  }
</style>
