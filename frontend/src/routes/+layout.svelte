<script>
  import '../app.css';
  import { page } from '$app/stores';
</script>

<div class="shell">
  <nav class="sidebar">
    <div class="logo">
      <span class="logo-goals">GOALS</span>
      <span class="logo-sub">La Liga ML</span>
    </div>

    <ul class="nav-list">
      <li>
        <a href="/" class:active={$page.url.pathname === '/'}>
          <span class="nav-icon">📅</span>
          Calendar
        </a>
      </li>
      <li>
        <a href="/stats" class:active={$page.url.pathname === '/stats'}>
          <span class="nav-icon">📊</span>
          Player Stats
        </a>
      </li>
    </ul>
  </nav>

  <main class="content">
    <slot />
  </main>
</div>

<style>
  .shell {
    display: flex;
    height: 100vh;
    overflow: hidden;
  }

  .sidebar {
    width: var(--sidebar-width);
    min-width: var(--sidebar-width);
    background: var(--bg-secondary);
    border-right: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    padding: 0;
  }

  .logo {
    padding: 24px 16px 20px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
  }

  .logo-goals {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: 2px;
    background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .logo-sub {
    font-size: 10px;
    color: var(--text-secondary);
    letter-spacing: 1px;
    margin-top: 2px;
  }

  .nav-list {
    list-style: none;
    padding: 12px 0;
  }

  .nav-list li a {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    color: var(--text-secondary);
    font-size: 13px;
    font-weight: 500;
    border-left: 3px solid transparent;
    transition: color 0.15s, border-color 0.15s, background 0.15s;
  }

  .nav-list li a:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
  }

  .nav-list li a.active {
    color: var(--text-primary);
    border-left-color: var(--accent-primary);
    background: rgba(255, 75, 68, 0.08);
  }

  .nav-icon {
    font-size: 15px;
  }

  .content {
    flex: 1;
    overflow-y: auto;
    background: var(--bg-primary);
  }
</style>
