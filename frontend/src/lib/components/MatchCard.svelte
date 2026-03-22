<script>
  import ProbabilityBar from './ProbabilityBar.svelte';

  export let match;

  function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  }
</script>

<div class="match-card">
  <div class="match-header">
    <div class="teams">
      <span class="team home">{match.home_team}</span>
      <span class="vs">vs</span>
      <span class="team away">{match.away_team}</span>
    </div>
    <div class="meta">
      {#if match.finished && match.home_score !== null}
        <span class="score-badge">
          FT {match.home_score}–{match.away_score}
        </span>
      {:else}
        <span class="date">{formatDate(match.match_date)}</span>
      {/if}
    </div>
  </div>

  <div class="prediction">
    <ProbabilityBar
      label="WIN"
      probability={match.prediction?.win_prob ?? null}
      color="var(--color-win)"
    />
    <ProbabilityBar
      label="DRAW"
      probability={match.prediction?.draw_prob ?? null}
      color="var(--color-draw)"
    />
    <ProbabilityBar
      label="LOSS"
      probability={match.prediction?.loss_prob ?? null}
      color="var(--color-loss)"
    />
  </div>
</div>

<style>
  .match-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 12px 14px;
    transition: border-color 0.15s;
  }

  .match-card:hover {
    border-color: var(--bg-tertiary);
  }

  .match-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }

  .teams {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  .team {
    font-weight: 600;
    font-size: 13px;
  }

  .vs {
    font-size: 11px;
    color: var(--text-secondary);
  }

  .meta {
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }

  .score-badge {
    background: var(--bg-tertiary);
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
  }

  .date {
    font-size: 12px;
    color: var(--text-secondary);
  }
</style>
