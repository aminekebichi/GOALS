<script>
  export let contributions = {}; // { metric_name: weighted_z_score }

  // Sort by absolute contribution, largest first
  $: sorted = Object.entries(contributions)
    .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a));

  // Max absolute value for scaling bars
  $: maxAbs = sorted.reduce((m, [, v]) => Math.max(m, Math.abs(v)), 0.001);

  function label(key) {
    const labels = {
      goals_assists: 'Goals + Assists',
      xg: 'xG',
      xa: 'xA',
      dribbles: 'Dribbles',
      shots: 'Shots on Target',
      chances_created: 'Chances Created',
      recoveries: 'Recoveries',
      prog_pass: 'Progressive Passes',
      tackles: 'Tackles',
      interceptions: 'Interceptions',
      aerials_won: 'Aerials Won',
      clearances: 'Clearances',
      shot_blocks: 'Shot Blocks',
      saves: 'Saves',
      xgot_faced: 'xGOT Faced',
      diving_saves: 'Diving Saves',
      saves_inside_box: 'Saves in Box',
      high_claims: 'High Claims',
      sweeper_actions: 'Sweeper Actions',
    };
    return labels[key] || key;
  }
</script>

<div class="breakdown">
  <div class="breakdown-title">Metric Contributions</div>
  {#each sorted as [key, value]}
    <div class="metric-row">
      <span class="metric-name">{label(key)}</span>
      <div class="metric-bar-track">
        <div
          class="metric-bar-fill"
          class:negative={value < 0}
          style="width: {Math.abs(value) / maxAbs * 100}%"
        />
      </div>
      <span class="metric-value" class:neg={value < 0}>
        {value > 0 ? '+' : ''}{value.toFixed(2)}
      </span>
    </div>
  {/each}
</div>

<style>
  .breakdown {
    padding: 10px 12px;
    background: var(--bg-primary);
    border-top: 1px solid var(--border-color);
  }

  .breakdown-title {
    font-size: 10px;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--text-secondary);
    margin-bottom: 10px;
    font-weight: 600;
  }

  .metric-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 5px 0;
  }

  .metric-name {
    width: 140px;
    font-size: 12px;
    color: var(--text-secondary);
    flex-shrink: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .metric-bar-track {
    flex: 1;
    height: 5px;
    background: var(--bg-tertiary);
    border-radius: 3px;
    overflow: hidden;
  }

  .metric-bar-fill {
    height: 100%;
    background: var(--accent-primary);
    border-radius: 3px;
    transition: width 0.3s ease;
  }

  .metric-bar-fill.negative {
    background: var(--color-loss);
  }

  .metric-value {
    width: 40px;
    text-align: right;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-primary);
    flex-shrink: 0;
  }

  .metric-value.neg {
    color: var(--color-loss);
  }
</style>
