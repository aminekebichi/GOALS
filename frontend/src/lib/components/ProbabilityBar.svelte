<script>
  export let label = '';
  export let probability = null; // null = no prediction yet
  export let color = 'var(--accent-primary)';
</script>

<div class="prob-row">
  <span class="prob-label">{label}</span>
  <div class="bar-track">
    {#if probability !== null}
      <div class="bar-fill" style="width: {probability * 100}%; background: {color};" />
    {:else}
      <div class="bar-fill placeholder" style="width: 100%;" />
    {/if}
  </div>
  <span class="prob-value">
    {#if probability !== null}
      {(probability * 100).toFixed(0)}%
    {:else}
      —
    {/if}
  </span>
</div>

<style>
  .prob-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 3px 0;
  }

  .prob-label {
    width: 120px;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-secondary);
    flex-shrink: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .bar-track {
    flex: 1;
    height: 6px;
    background: var(--bg-primary);
    border-radius: 3px;
    overflow: hidden;
  }

  .bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.4s ease;
  }

  .bar-fill.placeholder {
    background: var(--bg-tertiary);
  }

  .prob-value {
    width: 32px;
    text-align: right;
    font-size: 11px;
    font-weight: 600;
    color: var(--text-primary);
    flex-shrink: 0;
  }
</style>
