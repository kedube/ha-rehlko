import { css } from "lit";

// One stylesheet for the panel. Surfaces, text and status colours come from Home Assistant's
// own CSS variables, so the panel follows the active theme (light, dark and custom themes);
// the fallbacks are what the local preview shows.
export const panelStyles = css`
  :host {
    --rk-bg: var(--primary-background-color, #f3f4f6);
    --rk-card: var(--card-background-color, #fff);
    --rk-fg: var(--primary-text-color, #1a1a1a);
    --rk-muted: var(--secondary-text-color, #5f666d);
    --rk-divider: var(--divider-color, #e0e0e0);
    --rk-accent: var(--rehlko-accent-color, #1f8a4c);
    --rk-ok: var(--success-color, #1f8a4c);
    --rk-warn: var(--warning-color, #c98a00);
    --rk-bad: var(--error-color, #c0392b);
    --rk-util: var(--info-color, #2f6fb0);
    /* Coloured text is mixed with the text colour, so it stays readable on either theme. */
    --rk-accent-text: color-mix(in srgb, var(--rk-accent) 72%, var(--rk-fg));
    --rk-radius: var(--ha-card-border-radius, 12px);
    --rk-control-radius: 10px;
    display: block;
    height: 100%;
    overflow-y: auto;
    background: var(--rk-bg);
    color: var(--rk-fg);
    font-family: var(--ha-font-family-body, var(--paper-font-body1_-_font-family, Roboto, system-ui, sans-serif));
    -webkit-font-smoothing: antialiased;
  }
  * { box-sizing: border-box; }

  .wrap {
    max-width: 1100px;
    margin: 0 auto;
    padding: 16px;
    padding-bottom: max(24px, env(safe-area-inset-bottom));
  }

  header.bar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 4px 0 14px;
  }
  header.bar h1 {
    font-size: 22px;
    font-weight: 600;
    margin: 0;
    flex: 1;
    min-width: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .picker {
    background: var(--rk-card);
    color: var(--rk-fg);
    border: 1px solid var(--rk-divider);
    border-radius: var(--rk-control-radius);
    padding: 8px 10px;
    font: inherit;
    font-size: 14px;
    max-width: 45%;
  }
  .icon-button {
    flex: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border: 1px solid var(--rk-divider);
    border-radius: var(--rk-control-radius);
    background: var(--rk-card);
    color: var(--rk-muted);
    cursor: pointer;
  }
  .icon-button svg { width: 22px; height: 22px; }
  .icon-button:hover { color: var(--rk-fg); }
  .icon-button.spin svg { animation: spin 0.9s linear infinite; }
  button:disabled { opacity: 0.5; cursor: default; }
  button:focus-visible, a:focus-visible, select:focus-visible, input:focus-visible, textarea:focus-visible {
    outline: 2px solid var(--rk-util);
    outline-offset: 2px;
  }

  .card {
    min-width: 0;
    background: var(--rk-card);
    border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--rk-divider));
    border-radius: var(--rk-radius);
    box-shadow: var(--ha-card-box-shadow, none);
    padding: 16px;
  }

  .hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1.3fr);
    gap: 16px;
  }
  @media (max-width: 760px) {
    .hero { grid-template-columns: minmax(0, 1fr); }
  }
  :host([narrow]) .hero { grid-template-columns: minmax(0, 1fr); }

  .visual {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
    min-height: 260px;
    padding: 24px 20px;
  }
  .generator-product {
    width: 100%;
    max-width: 400px;
    margin: 0;
    text-align: center;
  }
  .generator-photo {
    display: block;
    width: 100%;
    height: auto;
    object-fit: contain;
  }
  .generator-product figcaption {
    margin-top: 12px;
    font-size: 12px;
    line-height: 1.4;
    color: var(--rk-muted);
  }
  .status-chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    font-size: 14px;
    padding: 6px 14px;
    border-radius: 999px;
    background: color-mix(in srgb, var(--chip) 14%, transparent);
    color: color-mix(in srgb, var(--chip) 72%, var(--rk-fg));
  }
  .status-dot {
    flex: none;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--chip);
  }
  .status-chip.live .status-dot { animation: pulse 1.6s ease-in-out infinite; }

  /* Utility ── Home ── Generator: the wire from whichever source feeds the home is lit. */
  .flow {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(14px, 44px) minmax(0, 1fr) minmax(14px, 44px) minmax(0, 1fr);
    align-items: center;
  }
  .node {
    --src: var(--rk-divider);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
    min-width: 0;
    padding: 12px 6px;
    border-radius: 12px;
    border: 1px solid var(--rk-divider);
    text-align: center;
    color: var(--rk-muted);
  }
  .node svg { width: 28px; height: 28px; }
  .node .label, .node .value { max-width: 100%; overflow-wrap: break-word; hyphens: auto; }
  .node .label { font-size: 12px; }
  .node .value { font-size: 15px; font-weight: 600; line-height: 1.25; color: var(--rk-fg); }
  .node.utility, .wire.utility { --src: var(--rk-util); }
  .node.generator, .wire.generator { --src: var(--rk-accent); }
  .node.active {
    border-color: var(--src);
    background: color-mix(in srgb, var(--src) 10%, transparent);
    color: color-mix(in srgb, var(--src) 72%, var(--rk-fg));
  }
  .node.down { border-color: var(--rk-bad); border-style: dashed; }
  .node.down .value { color: color-mix(in srgb, var(--rk-bad) 72%, var(--rk-fg)); }
  .wire {
    height: 3px;
    background: var(--rk-divider);
  }
  .wire.flowing {
    background: repeating-linear-gradient(90deg, var(--src) 0 7px, transparent 7px 12px);
    background-size: 12px 100%;
    animation: flow 0.7s linear infinite;
  }
  .wire.generator.flowing { animation-direction: reverse; }
  @media (max-width: 520px) {
    .flow { grid-template-columns: minmax(0, 1fr) 12px minmax(0, 1fr) 12px minmax(0, 1fr); }
    .node { padding: 10px 4px; }
    .node .value { font-size: 14px; }
  }

  .stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(112px, 1fr));
    gap: 10px;
    margin-top: 14px;
  }
  .stat {
    min-width: 0;
    border: 1px solid var(--rk-divider);
    border-radius: 12px;
    padding: 10px 12px;
  }
  .stat.wide { grid-column: span 2; }
  .stat .k { font-size: 11px; color: var(--rk-muted); text-transform: uppercase; letter-spacing: 0.4px; }
  .stat .v { font-size: 18px; font-weight: 600; margin-top: 2px; overflow-wrap: anywhere; }
  .stat.wide .v { font-size: 15px; line-height: 1.6; }
  .stat .u { font-size: 12px; color: var(--rk-muted); font-weight: 400; margin-inline-start: 3px; }

  .tabs {
    display: flex;
    gap: 4px;
    margin: 20px 0 12px;
    overflow-x: auto;
    scrollbar-width: none;
  }
  .tabs::-webkit-scrollbar { display: none; }
  .tabs button {
    flex: none;
    border: none;
    background: transparent;
    color: var(--rk-muted);
    font: inherit;
    font-size: 14px;
    font-weight: 600;
    padding: 9px 14px;
    border-radius: var(--rk-control-radius);
    cursor: pointer;
    white-space: nowrap;
  }
  .tabs button:hover { color: var(--rk-fg); }
  .tabs button[aria-selected="true"] {
    color: var(--rk-accent-text);
    background: color-mix(in srgb, var(--rk-accent) 14%, transparent);
  }

  .section { display: grid; gap: 12px; }
  .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(260px, 100%), 1fr)); gap: 12px; }

  .list { display: flex; flex-direction: column; }
  .list-item {
    display: flex;
    gap: 12px;
    padding: 11px 2px;
    border-bottom: 1px solid var(--rk-divider);
    align-items: flex-start;
  }
  .list-item:last-child { border-bottom: none; }
  .list-item .when { flex: none; width: 140px; font-size: 12px; color: var(--rk-muted); padding-top: 2px; }
  @media (max-width: 520px) {
    .list-item .when { width: 92px; }
  }
  .list-item .what { flex: 1; min-width: 0; }
  .list-item .what .title { font-weight: 600; font-size: 14px; overflow-wrap: anywhere; }
  .list-item .what .sub { font-size: 12px; color: var(--rk-muted); margin-top: 2px; }
  .sev { flex: none; width: 4px; border-radius: 2px; align-self: stretch; background: var(--rk-divider); }
  .sev.fault, .sev.shutdown { background: var(--rk-bad); }
  .sev.warning { background: var(--rk-warn); }
  .sev.notice, .sev.status { background: var(--rk-util); }
  .more { display: flex; justify-content: center; padding-top: 12px; }

  .kv { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 8px 16px; }
  .kv .key { color: var(--rk-muted); font-size: 14px; }
  .kv .val { font-size: 14px; font-weight: 500; text-align: end; overflow-wrap: anywhere; }

  /* Load-module and PIM settings: name, value or switch, and an edit button where writable. */
  .params { display: flex; flex-direction: column; gap: 2px; }
  .param { display: flex; align-items: center; gap: 12px; min-height: 34px; }
  .param .key { flex: 1; min-width: 0; color: var(--rk-muted); font-size: 14px; overflow-wrap: anywhere; }
  .param .val { font-size: 14px; font-weight: 500; text-align: end; overflow-wrap: anywhere; }
  .param input[type="checkbox"] { flex: none; width: 18px; height: 18px; accent-color: var(--rk-accent); cursor: pointer; }
  .icon-button.small { width: 32px; height: 32px; border-color: transparent; background: transparent; }
  .icon-button.small svg { width: 18px; height: 18px; }

  h2.card-title { margin: 0 0 12px; font-size: 16px; font-weight: 600; }

  .controls { display: grid; gap: 12px; }
  .btn-row { display: flex; flex-wrap: wrap; gap: 10px; }
  .btn-row.spaced { margin-top: 14px; }
  .btn-row.end { justify-content: flex-end; }
  .action {
    border: 1.5px solid var(--rk-accent);
    border-radius: 12px;
    padding: 10px 16px;
    font: inherit;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--rk-accent);
    color: #fff;
    text-decoration: none;
  }
  .action.ghost { background: transparent; color: var(--rk-accent-text); }
  .action.danger { background: var(--rk-bad); border-color: var(--rk-bad); }
  .action.ghost.danger { background: transparent; color: color-mix(in srgb, var(--rk-bad) 80%, var(--rk-fg)); }
  .action:disabled { opacity: 0.45; cursor: not-allowed; }
  .action svg { flex: none; width: 18px; height: 18px; }

  .field { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
  .field label { font-size: 13px; color: var(--rk-muted); font-weight: 600; }
  .field select, .field input, .field textarea {
    width: 100%;
    background: var(--rk-bg);
    border: 1px solid var(--rk-divider);
    border-radius: var(--rk-control-radius);
    padding: 9px 11px;
    color: var(--rk-fg);
    font: inherit;
    font-size: 14px;
  }
  .field textarea { resize: vertical; min-height: 64px; }
  .toggle { display: flex; align-items: center; gap: 10px; font-size: 14px; cursor: pointer; padding: 4px 0; }
  .toggle input { flex: none; width: 18px; height: 18px; accent-color: var(--rk-accent); }

  .banner {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    padding: 12px 14px;
    border-radius: 12px;
    font-size: 14px;
    line-height: 1.45;
    margin-bottom: 14px;
    --tone: var(--rk-util);
    background: color-mix(in srgb, var(--tone) 14%, transparent);
    color: var(--rk-fg);
  }
  .banner svg { width: 22px; height: 22px; flex: none; color: var(--tone); }
  .banner.bad { --tone: var(--rk-bad); }
  .banner.warn { --tone: var(--rk-warn); }
  .banner.info { --tone: var(--rk-util); }

  .scrim {
    position: fixed;
    inset: 0;
    z-index: 30;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    background: rgba(0, 0, 0, 0.45);
  }
  .dialog {
    width: min(420px, 100%);
    background: var(--rk-card);
    color: var(--rk-fg);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.35);
  }
  .dialog h2 { margin: 0 0 8px; font-size: 18px; font-weight: 600; }
  .dialog p { margin: 0 0 20px; font-size: 14px; line-height: 1.5; color: var(--rk-muted); }
  form.dialog { display: grid; gap: 14px; }
  form.dialog h2 { margin: 0; }
  form.dialog .btn-row { margin-top: 6px; }

  .toast {
    position: fixed;
    left: 50%;
    bottom: max(24px, env(safe-area-inset-bottom));
    transform: translateX(-50%);
    max-width: calc(100% - 32px);
    background: #262626;
    color: #fff;
    padding: 11px 18px;
    border-radius: 10px;
    font-size: 14px;
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.3);
    z-index: 40;
  }
  .toast.err { background: var(--rk-bad); }

  .empty { color: var(--rk-muted); font-size: 14px; line-height: 1.5; padding: 20px 0; text-align: center; }
  .card.empty { padding: 32px 20px; }
  .card.empty p { margin: 0 auto 16px; max-width: 520px; }
  .hint { color: var(--rk-muted); font-size: 13px; line-height: 1.45; margin: 10px 0 0; }
  .muted { color: var(--rk-muted); margin: 0; }
  .pill {
    font-size: 11px;
    font-weight: 500;
    padding: 2px 8px;
    border-radius: 999px;
    background: var(--rk-bg);
    color: var(--rk-muted);
    vertical-align: middle;
  }

  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
  @keyframes flow { to { background-position: 12px 0; } }
  @keyframes spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) {
    .status-chip.live .status-dot, .icon-button.spin svg { animation: none; }
    .wire.flowing { animation: none; background: var(--src); }
  }
`;
