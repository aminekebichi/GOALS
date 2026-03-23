<script>
  import '../app.css';
</script>

<div class="shell">
  <header class="top-bar">
    <div class="brand">
      <span class="brand-title">GOALS</span>
      <span class="brand-sub">La Liga · ML Match Predictions</span>
    </div>
  </header>
  <main class="content">
    <slot />
  </main>
</div>

<style>
  .shell {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    background: var(--bg-primary);
  }

  .top-bar {
    border-bottom: 1px solid var(--border-color);
    background: var(--bg-secondary);
    padding: 16px 24px;
    display: flex;
    justify-content: center;
  }

  .brand {
    display: flex;
    align-items: baseline;
    gap: 12px;
  }

  .brand-title {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: 3px;
    background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .brand-sub {
    font-size: 11px;
    color: var(--text-secondary);
    letter-spacing: 1px;
    text-transform: uppercase;
  }

  .content {
    flex: 1;
    overflow-y: auto;
  }
</style>
