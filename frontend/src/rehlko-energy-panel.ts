import { LitElement, html, nothing, type PropertyValues, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { keyed } from "lit/directives/keyed.js";
import { live } from "lit/directives/live.js";
import { mdiRefresh, mdiPlayCircle, mdiStopCircle, mdiClockCheckOutline, mdiAlertOctagon,
  mdiCarBrakeAlert, mdiTransmissionTower, mdiEngine, mdiHomeLightningBolt, mdiCalendarEdit,
  mdiNotePlusOutline, mdiMenu, mdiCloudOffOutline, mdiAlertCircleOutline, mdiOpenInNew,
  mdiCalendarRemove, mdiPencil } from "@mdi/js";
import { panelStyles } from "./styles";
import { generatorImage, generatorState, type VisualState } from "./generator-visual";
import {
  DEFAULT_FORMAT, addressText, fmtDateTime, fmtDays, fmtDuration, fmtNumber, fmtRelative,
  formatFrom, fromInputValue, humanize, power, pressure, slugify, temperature, toInputValue,
  type Format,
} from "./format";
import { localizer, type Localize, type MessageKey } from "./localize";
import type { Account, Generator, HomeAssistant, PeripheralParam, Snapshot, SnapshotMessage } from "./types";

type Tab = "overview" | "controls" | "activity" | "maintenance" | "profile" | "diagnostics";
const TABS: Tab[] = ["overview", "controls", "activity", "maintenance", "profile", "diagnostics"];
const EXERCISE_MODES = ["Unloaded", "UnloadedFullSpeed", "LoadedFullSpeed", "EcoExercise"];
const EXERCISE_FREQUENCIES = ["Weekly", "EveryOtherWeek", "Monthly"];
const PAGE = 50; // list rows shown at first, and added by each "Show more"

// Where the integration's translations keep each enum's state names. The panel shows the
// same wire values, so it reads the same translations (through `hass.localize`).
const ENUM = {
  status: "sensor.status.state",
  engine: "sensor.engine_state.state",
  switchState: "sensor.switch_state.state",
  powerSource: "sensor.power_source.state",
  mode: "select.exercise_mode.state",
  frequency: "select.exercise_frequency.state",
  level: "event.activity.state_attributes.event_type.state",
  notification: "event.notifications.state_attributes.event_type.state",
  fuel: "sensor.fuel_type.state",
  cooling: "sensor.cooling_type.state",
  connection: "sensor.connection_type.state",
  agreement: "sensor.service_agreement_status.state",
  cellular: "sensor.cellular_data_status.state",
  atsPosition: "sensor.ats_power_source.state",
} as const;

// `/homeowner/settings/notification` flags and the switch entity that carries each one's name.
const NOTIFY_SWITCH: Record<string, string> = {
  sendShutdowns: "notify_shutdowns", sendWarnings: "notify_warnings",
  sendGeneratorRunningNotices: "notify_running", sendNotices: "notify_notices",
  sendConnectionNotices: "notify_connection", sendMaintenanceNotices: "notify_maintenance",
  sendLongRunningNotices: "notify_long_running", sendNotificationEmails: "notify_emails",
  sendPushNotifications: "notify_push",
};

const STATUS_TEXT: Record<Exclude<VisualState, "standby" | "running">, MessageKey> = {
  offline: "status.offline", estop: "status.estop", fault: "status.fault",
  exercising: "status.exercising",
};

interface Confirm { title: string; text: string; action: string; danger: boolean; run: () => void }
/** A load-module or PIM setting being edited: its name, and its value unless that is a switch. */
interface Editing { definitionId: number | string; name: string; value: unknown }

function icon(path: string): TemplateResult {
  return html`<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d=${path} /></svg>`;
}

function errorMessage(err: unknown, fallback: string): string {
  return typeof err === "object" && err !== null && "message" in err && typeof err.message === "string"
    ? err.message : fallback;
}

function generatorKey(gen: Generator): string {
  return `${gen.entry_id}:${gen.device_id}`;
}

@customElement("rehlko-energy-panel")
export class RehlkoEnergyPanel extends LitElement {
  static override styles = panelStyles;

  @property({ attribute: false }) hass?: HomeAssistant;
  @property({ attribute: false }) panel?: unknown;
  @property({ type: Boolean, reflect: true }) narrow = false;

  @state() private snapshot: Snapshot = { generators: [], accounts: [] };
  @state() private selected: string | null = null;
  @state() private tab: Tab = "overview";
  @state() private busy = false;
  @state() private toast: { text: string; err: boolean } | null = null;
  @state() private connectionError: string | null = null;
  @state() private receivedSnapshot = false;
  @state() private confirm: Confirm | null = null;
  @state() private editing: Editing | null = null;
  @state() private eventLimit = PAGE;
  @state() private notificationLimit = PAGE;

  private t: Localize = localizer();
  private fmt: Format = DEFAULT_FORMAT;
  private unsub?: () => void;
  private toastTimer?: number;
  private retryTimer?: number;
  private subscriptionConnection?: HomeAssistant["connection"];
  private subscriptionGeneration = 0;
  private restoreFocus?: HTMLElement | null;
  private translationsFor?: string;

  override connectedCallback(): void {
    super.connectedCallback();
    void this.subscribe();
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    this.stopSubscription();
    clearTimeout(this.toastTimer);
  }

  override shouldUpdate(changed: PropertyValues): boolean {
    // HA replaces hass on every entity change; the panel's data comes from its own
    // subscription. Re-render only for what the panel reads from hass: the connection, the
    // viewer's language/locale/units, the loaded translations and the sidebar mode.
    if ([...changed.keys()].some((key) => key !== "hass")) return true;
    const previous = changed.get("hass") as HomeAssistant | undefined;
    const hass = this.hass;
    return previous?.connection !== hass?.connection
      || previous?.language !== hass?.language
      || previous?.locale !== hass?.locale
      || previous?.localize !== hass?.localize
      || previous?.config !== hass?.config
      || previous?.dockedSidebar !== hass?.dockedSidebar;
  }

  override willUpdate(changed: PropertyValues): void {
    if (changed.has("hass")) {
      this.t = localizer(this.hass?.locale?.language ?? this.hass?.language);
      this.fmt = formatFrom(this.hass);
      this.loadEntityTranslations();
    }
  }

  override updated(changed: PropertyValues): void {
    if (changed.has("hass")) void this.subscribe();
    if (changed.has("confirm")) {
      if (this.confirm) this.field<HTMLButtonElement>("confirm-cancel")?.focus();
      else this.restoreFocus?.focus();
    }
    if (changed.has("editing")) {
      if (this.editing) this.field<HTMLInputElement>("edit-name")?.select();
      else this.restoreFocus?.focus();
    }
  }

  private stopSubscription(): void {
    this.subscriptionGeneration++;
    this.unsub?.();
    this.unsub = undefined;
    this.subscriptionConnection = undefined;
    clearTimeout(this.retryTimer);
  }

  private async subscribe(): Promise<void> {
    if (!this.isConnected || !this.hass || this.subscriptionConnection === this.hass.connection) return;
    this.stopSubscription();
    const generation = this.subscriptionGeneration;
    this.subscriptionConnection = this.hass.connection;
    try {
      const unsub = await this.hass.connection.subscribeMessage<SnapshotMessage>(
        (msg) => {
          if (generation === this.subscriptionGeneration && this.isConnected) this.onSnapshot(msg);
        },
        { type: "rehlko_energy/subscribe" },
      );
      if (generation !== this.subscriptionGeneration || !this.isConnected) {
        unsub();
        return;
      }
      this.unsub = unsub;
    } catch (err) {
      if (generation !== this.subscriptionGeneration || !this.isConnected) return;
      this.subscriptionConnection = undefined;
      this.connectionError = errorMessage(err, this.t("connection.failed"));
      this.retryTimer = window.setTimeout(() => { void this.subscribe(); }, 5000);
    }
  }

  private onSnapshot(message: SnapshotMessage): void {
    // The server leaves out the bulky fields that have not changed; keep the copies we have.
    const before = new Map(this.snapshot.generators.map((g) => [generatorKey(g), g]));
    const snapshot: Snapshot = {
      accounts: message.accounts,
      generators: message.generators.map((g) => {
        const had = before.get(`${g.entry_id}:${g.device_id}`);
        return {
          ...g,
          events: g.events ?? had?.events ?? [],
          notifications: g.notifications ?? had?.notifications ?? [],
          maintenance_notes: g.maintenance_notes ?? had?.maintenance_notes ?? [],
          entities: g.entities ?? had?.entities ?? {},
        };
      }),
    };
    this.snapshot = snapshot;
    this.receivedSnapshot = true;
    this.connectionError = null;
    if (this.selected === null || !snapshot.generators.some((g) => generatorKey(g) === this.selected)) {
      this.selected = snapshot.generators[0] ? generatorKey(snapshot.generators[0]) : null;
    }
  }

  private get current(): Generator | undefined {
    return this.snapshot.generators.find((g) => generatorKey(g) === this.selected);
  }

  private account(entryId: string): Account | undefined {
    return this.snapshot.accounts.find((a) => a.entry_id === entryId);
  }

  private showToast(text: string, err = false): void {
    this.toast = { text, err };
    clearTimeout(this.toastTimer);
    this.toastTimer = window.setTimeout(() => (this.toast = null), 4000);
  }

  private async call(service: string, data: Record<string, unknown>, done: MessageKey): Promise<boolean> {
    if (this.busy || !this.hass) return false;
    const gen = this.current;
    if (!gen || !gen.ha_device_id) {
      this.showToast(this.t("toast.no_device"), true);
      return false;
    }
    this.busy = true;
    try {
      await this.hass.callService("rehlko_energy", service, { device_id: gen.ha_device_id, ...data });
      this.showToast(this.t(done));
      return true;
    } catch (err) {
      this.showToast(errorMessage(err, this.t("toast.failed")), true);
      return false;
    } finally {
      this.busy = false;
    }
  }

  /** Make sure the frontend has this integration's entity translations in this language. */
  private loadEntityTranslations(): void {
    const hass = this.hass;
    const language = hass?.language;
    if (!hass?.loadBackendTranslation || !language || this.translationsFor === language) return;
    this.translationsFor = language;
    // Home Assistant swaps `hass.localize` when they arrive, which re-renders the panel.
    hass.loadBackendTranslation("entity", "rehlko_energy").catch(() => {
      this.translationsFor = undefined;
    });
  }

  /** An enum value's name in the viewer's language, from the integration's translations. */
  private label(group: string, value: unknown): string {
    if (value === null || value === undefined || value === "") return "";
    return this.hass?.localize?.(`component.rehlko_energy.entity.${group}.${slugify(value)}`) || humanize(value);
  }

  private notifyLabel(key: string): string {
    const entity = NOTIFY_SWITCH[key];
    return (entity && this.hass?.localize?.(`component.rehlko_energy.entity.switch.${entity}.name`))
      || humanize(key.replace(/^send/, ""));
  }

  override render(): TemplateResult {
    const t = this.t;
    const gen = this.current;
    const showMenu = this.narrow || this.hass?.dockedSidebar === "always_hidden";
    return html`
      <div class="wrap">
        <header class="bar">
          ${showMenu
            ? html`<button class="icon-button" aria-label=${t("common.open_sidebar")} @click=${this.toggleMenu}>${icon(mdiMenu)}</button>`
            : nothing}
          <h1>${gen ? gen.name : t("common.generator")}</h1>
          ${this.snapshot.generators.length > 1
            ? html`<select class="picker" aria-label=${t("common.generator")} @change=${this.onPick}>
                ${this.snapshot.generators.map(
                  (g) => html`<option value=${generatorKey(g)} ?selected=${generatorKey(g) === this.selected}>${g.name}</option>`,
                )}
              </select>`
            : nothing}
          <button class=${`icon-button ${this.busy ? "spin" : ""}`} title=${t("common.refresh")} aria-label=${t("common.refresh")}
            ?disabled=${this.busy} @click=${this.refresh}>${icon(mdiRefresh)}</button>
        </header>
        ${this.connectionError
          ? html`<div class="banner bad" role="alert">${icon(mdiCloudOffOutline)}<span>${this.connectionError} ${t("connection.retrying")}</span></div>`
          : nothing}
        ${gen ? keyed(generatorKey(gen), this.renderGenerator(gen)) : this.renderEmpty()}
      </div>
      ${this.renderConfirm()}
      ${this.renderEdit()}
      ${this.toast ? html`<div role="status" class=${`toast ${this.toast.err ? "err" : ""}`}>${this.toast.text}</div>` : nothing}
    `;
  }

  private renderEmpty(): TemplateResult {
    const t = this.t;
    if (!this.receivedSnapshot) {
      return html`<div class="card empty">${this.connectionError ? t("empty.unavailable") : t("empty.connecting")}</div>`;
    }
    const message = this.snapshot.accounts.some((account) => !account.loaded)
      ? t("empty.not_loaded")
      : this.snapshot.accounts.length ? t("empty.no_generators") : t("empty.no_integration");
    return html`<div class="card empty">
      <p>${message}</p>
      ${this.link("/config/integrations/integration/rehlko_energy", t("empty.open_integrations"), "action ghost")}
    </div>`;
  }

  private renderGenerator(gen: Generator): TemplateResult {
    const d = gen.derived;
    const hasCriticalFault = gen.alerts.some((a) => a.isCriticalFault);
    const vstate = generatorState({ ...d, hasCriticalFault });
    const product = generatorImage(gen);
    const active = vstate === "running" || vstate === "exercising";

    return html`
      ${this.renderBanner(gen, hasCriticalFault)}
      <div class="hero">
        <div class="card visual" style=${`--chip:${this.chipColor(vstate)}`}>
          <figure class="generator-product">
            <img class="generator-photo" src=${product.src} alt=${this.t("image.alt", { model: product.description })}
              width=${product.width} height=${product.height} decoding="async" draggable="false" />
            <figcaption>${product.representative ? this.t("image.representative") : product.caption}</figcaption>
          </figure>
          <span class=${`status-chip ${active ? "live" : ""}`}><span class="status-dot"></span>${this.statusText(gen, vstate)}</span>
        </div>
        <div class="card">
          ${this.renderFlow(gen)}
          ${this.renderStats(gen)}
        </div>
      </div>

      <div class="tabs" role="tablist" @keydown=${this.onTabKey}>
        ${TABS.map(
          (tab) => html`<button role="tab" id=${`tab-${tab}`} aria-controls="tabpanel" aria-selected=${this.tab === tab}
            tabindex=${this.tab === tab ? 0 : -1} @click=${() => (this.tab = tab)}>${this.t(`tab.${tab}`)}</button>`,
        )}
      </div>
      <div id="tabpanel" role="tabpanel" aria-labelledby=${`tab-${this.tab}`}>${this.renderTab(gen)}</div>
    `;
  }

  private renderBanner(gen: Generator, hasCriticalFault: boolean): TemplateResult | typeof nothing {
    const t = this.t;
    const d = gen.derived;
    const banner = (kind: string, path: string, title: string, text: string) =>
      html`<div class=${`banner ${kind}`} role="status">${icon(path)}<span><strong>${title}</strong> ${text}</span></div>`;
    if (!gen.available || this.connectionError) {
      return html`<div class="banner warn" role="status">${icon(mdiAlertCircleOutline)}<span>${t("banner.stale")}</span></div>`;
    }
    if (!d.is_connected) {
      return banner("warn", mdiCloudOffOutline, t("banner.offline.title"), t("banner.offline.text"));
    }
    if (d.e_stop_engaged) {
      return banner("bad", mdiCarBrakeAlert, t("banner.estop.title"), t("banner.estop.text"));
    }
    if (hasCriticalFault) {
      const names = gen.alerts.filter((a) => a.isCriticalFault).map((a) => a.name || humanize(a.deviceEventId)).join(", ");
      return banner("bad", mdiAlertOctagon, t("banner.fault.title"), names);
    }
    if (d.utility_present === false && d.is_running) {
      return banner("info", mdiHomeLightningBolt, t("banner.outage.title"), t("banner.outage.text"));
    }
    return nothing;
  }

  private renderFlow(gen: Generator): TemplateResult {
    const t = this.t;
    const d = gen.derived;
    const onGenerator = d.on_generator_power;
    const onUtility = !onGenerator && d.utility_present === true;
    const volts = (value: unknown) => {
      const text = fmtNumber(value, this.fmt);
      return text === null ? null : `${text} V`;
    };
    const utility = d.utility_present === false
      ? t("flow.out")
      : volts(gen.details["utilityVoltageV"]) ?? (d.utility_present ? t("common.on") : "—");
    const generator = d.is_running
      ? volts(gen.details["generatorVoltageAvgV"]) ?? t("status.running")
      : t("status.standby");
    const source = onGenerator ? "Generator" : onUtility ? "Utility" : null;

    return html`<div class="flow">
      <div class=${`node utility ${onUtility ? "active" : ""} ${d.utility_present === false ? "down" : ""}`}>
        ${icon(mdiTransmissionTower)}
        <span class="label">${t("flow.utility")}</span>
        <span class="value">${utility}</span>
      </div>
      <div class=${`wire utility ${onUtility ? "flowing" : ""}`}></div>
      <div class=${`node home ${onGenerator ? "generator" : onUtility ? "utility" : ""} ${source ? "active" : ""}`}>
        ${icon(mdiHomeLightningBolt)}
        <span class="label">${t("flow.home")}</span>
        <span class="value">${source ? this.label(ENUM.powerSource, source) : "—"}</span>
      </div>
      <div class=${`wire generator ${onGenerator ? "flowing" : ""}`}></div>
      <div class=${`node generator ${onGenerator ? "active" : ""}`}>
        ${icon(mdiEngine)}
        <span class="label">${t("common.generator")}</span>
        <span class="value">${generator}</span>
      </div>
    </div>`;
  }

  private renderStats(gen: Generator): TemplateResult {
    const t = this.t;
    const f = this.fmt;
    const det = gen.details;
    const oil = pressure(det["engineOilPressurePsi"], f);
    const coolant = temperature(det["engineCoolantTempF"], f);
    const load = gen.derived.is_running ? power(gen.derived.load_w, f) : null;
    const engine = this.label(ENUM.engine, det["engineState"]);
    const stats: Array<[MessageKey, string | null | undefined, string?]> = [
      ["stat.load", load?.text, load?.unit],
      ["stat.speed", fmtNumber(det["engineSpeedRpm"], f), t("unit.rpm")],
      ["stat.frequency", fmtNumber(det["engineFrequencyHz"], f, 1), "Hz"],
      ["stat.battery", fmtNumber(det["batteryVoltageV"], f, 1), "V"],
      ["stat.oil_pressure", oil?.text, oil?.unit],
      ["stat.coolant", coolant?.text, coolant?.unit],
      ["stat.fuel", fmtNumber(det["fuelLevelPercent"], f), "%"],
      ["stat.total_runtime", fmtNumber(det["totalRuntimeHours"] ?? gen.device["totalRuntimeHours"], f, 1), "h"],
    ];
    return html`<div class="stat-grid">
      ${engine ? html`<div class="stat wide"><div class="k">${t("stat.engine")}</div><div class="v">${engine}</div></div>` : nothing}
      ${stats.filter(([, value]) => value !== null && value !== undefined).map(
        ([key, value, unit]) => html`<div class="stat"><div class="k">${t(key)}</div><div class="v">${value}${unit ? html`<span class="u">${unit}</span>` : nothing}</div></div>`,
      )}
    </div>`;
  }

  private renderTab(gen: Generator): TemplateResult {
    switch (this.tab) {
      case "overview": return this.renderOverview(gen);
      case "controls": return this.renderControls(gen);
      case "activity": return this.renderActivity(gen);
      case "maintenance": return this.renderMaintenance(gen);
      case "profile": return this.renderProfile(gen);
      case "diagnostics": return this.renderDiagnostics(gen);
    }
  }

  private renderOverview(gen: Generator): TemplateResult {
    const t = this.t;
    const f = this.fmt;
    const det = gen.details;
    const ex = det.exercise ?? {};
    const dev = gen.device;
    const alerts = gen.alerts;
    return html`<div class="section">
      <div class="grid-2">
        <div class="card">
          <h2 class="card-title">${t("overview.status")}</h2>
          <div class="kv">
            ${this.kv(t("overview.state"), this.label(ENUM.status, dev["status"]))}
            ${this.kv(t("overview.mode_switch"), this.label(ENUM.switchState, det["switchState"]))}
            ${this.kv(t("overview.power_source"), this.label(ENUM.powerSource, det["powerSource"]))}
            ${this.kv(t("overview.last_run"), fmtRelative(det["lastRanTimestamp"], f))}
            ${this.kv(t("overview.active_alerts"), fmtNumber(alerts.length || dev["alertCount"] || 0, f))}
            ${dev["shutdownReason"] && dev["shutdownReason"] !== "None" ? this.kv(t("overview.shutdown_reason"), humanize(dev["shutdownReason"])) : nothing}
          </div>
        </div>
        <div class="card">
          <h2 class="card-title">${t("overview.next_exercise")}</h2>
          ${gen.derived.has_schedule
            ? html`<div class="kv">
                ${this.kv(t("overview.when"), fmtDateTime(ex.nextStartTimestamp, f))}
                ${this.kv(t("field.mode"), this.label(ENUM.mode, ex.mode))}
                ${this.kv(t("field.frequency"), this.label(ENUM.frequency, ex.frequency))}
                ${this.kv(t("field.duration"), fmtDuration(ex.durationMinutes, f))}
                ${this.kv(t("overview.last_exercise"), fmtRelative(ex.lastStartTimestamp, f))}
              </div>`
            : html`<p class="empty">${t("overview.no_schedule")}</p>`}
        </div>
      </div>
      ${alerts.length
        ? html`<div class="card">
            <h2 class="card-title">${t("overview.active_alerts")}</h2>
            <div class="list">
              ${alerts.map(
                (a) => html`<div class="list-item">
                  <div class=${`sev ${slugify(a.level)}`}></div>
                  <div class="when">${fmtRelative(a.timestamp, f)}</div>
                  <div class="what">
                    <div class="title">${a.name || humanize(a.deviceEventId)}</div>
                    <div class="sub">${[
                      this.label(ENUM.level, a.level),
                      a.isCriticalFault ? t("alert.critical") : "",
                    ].filter(Boolean).join(" · ")}</div>
                  </div>
                </div>`,
              )}
            </div>
          </div>`
        : nothing}
    </div>`;
  }

  private renderControls(gen: Generator): TemplateResult {
    const t = this.t;
    const d = gen.derived;
    const ex = gen.details.exercise ?? {};
    const canAct = gen.available && !this.connectionError && d.is_connected;
    const canStart = canAct && d.ready_to_run && !d.e_stop_engaged && d.supports_exercise_scheduling;
    const schedulable = d.supports_exercise_scheduling;

    return html`<div class="controls">
      <div class="card">
        <h2 class="card-title">${t("controls.remote_exercise")}</h2>
        <div class="btn-row">
          <button class="action" ?disabled=${!canStart || this.busy || d.is_exercising} @click=${this.askStart}>
            ${icon(mdiPlayCircle)} ${t("controls.start")}
          </button>
          <button class="action danger ghost" ?disabled=${!canAct || this.busy || !d.is_exercising}
            @click=${() => this.call("stop_exercise", {}, "toast.exercise_stopped")}>
            ${icon(mdiStopCircle)} ${t("controls.stop")}
          </button>
        </div>
        ${!d.ready_to_run && canAct
          ? html`<p class="hint">${t("controls.start_hint", { status: this.label(ENUM.status, gen.device["status"]) || t("common.unknown") })}</p>`
          : nothing}
      </div>

      ${schedulable
        ? html`<div class="card">
            <h2 class="card-title">${d.has_schedule ? t("controls.schedule") : t("controls.create_schedule")}</h2>
            <div class="grid-2">
              <div class="field">
                <label for="freq">${t("field.frequency")}</label>
                <select id="freq" .value=${(ex.frequency as string) || "EveryOtherWeek"}>
                  ${EXERCISE_FREQUENCIES.map((v) => html`<option value=${v} ?selected=${(ex.frequency || "EveryOtherWeek") === v}>${this.label(ENUM.frequency, v)}</option>`)}
                </select>
              </div>
              <div class="field">
                <label for="mode">${t("field.mode")}</label>
                <select id="mode" .value=${(ex.mode as string) || "Unloaded"}>
                  ${EXERCISE_MODES.map((v) => html`<option value=${v} ?selected=${(ex.mode || "Unloaded") === v}>${this.label(ENUM.mode, v)}</option>`)}
                </select>
              </div>
              <div class="field">
                <label for="dur">${t("controls.duration_minutes")}</label>
                <input id="dur" type="number" inputmode="numeric" min="5" max="60" step="1" required .value=${String(ex.durationMinutes ?? 20)} />
              </div>
              ${d.supports_next_exercise_datetime
                ? html`<div class="field">
                    <label for="next">${t("controls.next_start")}</label>
                    <input id="next" type="datetime-local" .value=${toInputValue(ex.nextStartTimestamp, this.fmt)} />
                  </div>`
                : nothing}
            </div>
            <div class="btn-row spaced">
              <button class="action" ?disabled=${!canAct || this.busy} @click=${this.saveSchedule}>${icon(mdiCalendarEdit)} ${t("controls.save_schedule")}</button>
              ${d.has_schedule
                ? html`<button class="action ghost danger" ?disabled=${!canAct || this.busy} @click=${this.askDelete}>${icon(mdiCalendarRemove)} ${t("controls.delete_schedule")}</button>`
                : nothing}
            </div>
          </div>`
        : html`<div class="card"><p class="muted">${t("controls.no_scheduling")}</p></div>`}

      <div class="card">
        <h2 class="card-title">${t("controls.controller")}</h2>
        <div class="btn-row">
          <button class="action ghost" ?disabled=${!canAct || this.busy}
            @click=${() => this.call("sync_controller_clock", {}, "toast.clock_synced")}>${icon(mdiClockCheckOutline)} ${t("controls.sync_clock")}</button>
        </div>
        <p class="hint">${t("controls.controller_clock", { time: fmtDateTime(gen.details["controllerClockTimestamp"], this.fmt) })}</p>
      </div>

      <div class="card">
        <h2 class="card-title">${t("controls.add_note")}</h2>
        <div class="field"><textarea id="note" aria-label=${t("controls.note_label")} maxlength="2000" rows="2" placeholder=${t("controls.note_placeholder")}></textarea></div>
        <div class="btn-row spaced">
          <button class="action ghost" ?disabled=${this.busy} @click=${this.saveNote}>${icon(mdiNotePlusOutline)} ${t("controls.add_note_button")}</button>
        </div>
      </div>

      ${this.renderNotificationToggles(gen)}
    </div>`;
  }

  private renderNotificationToggles(gen: Generator): TemplateResult | typeof nothing {
    const account = this.account(gen.entry_id);
    const settings = account?.notification_settings;
    if (!settings) return nothing;
    return html`<div class="card">
      <h2 class="card-title">${this.t("controls.notifications")}</h2>
      <div class="grid-2">
        ${Object.entries(settings).filter(([, v]) => typeof v === "boolean").map(
          ([k, v]) => html`<label class="toggle">
            <input type="checkbox" .checked=${live(v)} ?disabled=${this.busy || !account?.notification_entities?.[k]} @change=${(e: Event) => this.toggleNotify(gen, k, (e.target as HTMLInputElement).checked)} />
            <span>${this.notifyLabel(k)}</span>
          </label>`,
        )}
      </div>
    </div>`;
  }

  private renderActivity(gen: Generator): TemplateResult {
    const t = this.t;
    const f = this.fmt;
    const events = gen.events;
    const notifications = gen.notifications;
    const more = (shown: number, total: number, grow: () => void) => total > shown
      ? html`<div class="more"><button class="action ghost" @click=${grow}>${t("common.show_more")}</button></div>`
      : nothing;
    return html`<div class="section">
      <div class="card">
        <h2 class="card-title">${t("activity.log")} <span class="pill">${fmtNumber(events.length, f)}</span></h2>
        ${events.length
          ? html`<div class="list">${events.slice(0, this.eventLimit).map(
              (e) => html`<div class="list-item">
                <div class=${`sev ${slugify(e.level)}`}></div>
                <div class="when">${fmtDateTime(e.timestamp, f)}</div>
                <div class="what">
                  <div class="title">${e.name || humanize(e.deviceEventId || e.event)}</div>
                  <div class="sub">${[
                    this.label(ENUM.level, e.level),
                    e.type ? humanize(e.type) : "",
                    e.fmi && e.fmi !== "swaggerGeneratedUnknown" ? t("activity.fmi", { value: humanize(e.fmi) }) : "",
                  ].filter(Boolean).join(" · ")}</div>
                </div>
              </div>`,
            )}</div>${more(this.eventLimit, events.length, () => (this.eventLimit += PAGE))}`
          : html`<p class="empty">${t("activity.none")}</p>`}
      </div>
      <div class="card">
        <h2 class="card-title">${t("activity.notifications")} <span class="pill">${fmtNumber(notifications.length, f)}</span></h2>
        ${notifications.length
          ? html`<div class="list">${notifications.slice(0, this.notificationLimit).map(
              (n) => html`<div class="list-item">
                <div class=${`sev ${slugify(n.type)}`}></div>
                <div class="when">${fmtRelative(n.timestamp, f)}</div>
                <div class="what">
                  <div class="title">${n.message || this.label(ENUM.notification, n.type)}</div>
                  <div class="sub">${[this.label(ENUM.notification, n.type), n.isEStopEvent ? t("activity.estop") : ""].filter(Boolean).join(" · ")}</div>
                </div>
              </div>`,
            )}</div>${more(this.notificationLimit, notifications.length, () => (this.notificationLimit += PAGE))}`
          : html`<p class="empty">${t("activity.no_notifications")}</p>`}
      </div>
    </div>`;
  }

  private renderMaintenance(gen: Generator): TemplateResult {
    const t = this.t;
    const f = this.fmt;
    const dev = gen.device;
    const notes = gen.maintenance_notes;
    const runtime = fmtNumber(gen.details["runtimeSinceLastMaintenanceHours"], f, 1);
    return html`<div class="section">
      <div class="card">
        <h2 class="card-title">${t("maintenance.title")}</h2>
        <div class="kv">
          ${this.kv(t("maintenance.last"), fmtDateTime(dev["lastMaintenanceTimestamp"], f))}
          ${this.kv(t("maintenance.next"), fmtDateTime(dev["nextMaintenanceTimestamp"], f))}
          ${this.kv(t("maintenance.interval"), dev["maintenancePeriodDays"] ? fmtDays(dev["maintenancePeriodDays"], f) : "—")}
          ${this.kv(t("maintenance.runtime_since"), runtime === null ? "—" : `${runtime} h`)}
        </div>
      </div>
      <div class="card">
        <h2 class="card-title">${t("maintenance.history")} <span class="pill">${fmtNumber(notes.length, f)}</span></h2>
        ${notes.length
          ? html`<div class="list">${notes.map(
              (n) => html`<div class="list-item">
                <div class="when">${fmtDateTime(n.timestamp, f)}</div>
                <div class="what">
                  <div class="title">${n.contents}</div>
                  <div class="sub">${n.authorIsDealer ? [t("maintenance.dealer"), n.dealerAuthor].filter(Boolean).join(" · ") : t("maintenance.homeowner")}</div>
                </div>
              </div>`,
            )}</div>`
          : html`<p class="empty">${t("maintenance.none")}</p>`}
      </div>
    </div>`;
  }

  private renderProfile(gen: Generator): TemplateResult {
    const t = this.t;
    const dev = gen.device;
    const det = gen.details;
    const dealer = (dev.dealerOrgs?.[0] ?? {}) as Record<string, unknown>;
    const sa = (det["serviceAgreement"] ?? {}) as Record<string, unknown>;
    const rated = fmtNumber(det["setOutputVoltageV"], this.fmt);
    return html`<div class="section">
      <div class="grid-2">
        <div class="card">
          <h2 class="card-title">${t("common.generator")}</h2>
          <div class="kv">
            ${this.kv(t("profile.model"), dev["modelDisplayName"] || humanize(dev["model"]))}
            ${this.kv(t("profile.serial"), dev["serialNumber"])}
            ${this.kv(t("profile.controller"), dev["controllerType"] || humanize(dev["product"]))}
            ${this.kv(t("profile.firmware"), dev["firmwareVersion"] || dev["currentFirmware"])}
            ${this.kv(t("profile.fuel"), this.label(ENUM.fuel, det["fuelType"]))}
            ${this.kv(t("profile.cooling"), this.label(ENUM.cooling, det["coolingType"]))}
            ${this.kv(t("profile.rated_voltage"), rated === null ? "—" : `${rated} V`)}
          </div>
        </div>
        <div class="card">
          <h2 class="card-title">${t("profile.site")}</h2>
          <div class="kv">
            ${this.kv(t("profile.address"), addressText(dev["address"] as never) || "—")}
            ${this.kv(t("profile.connection"), this.label(ENUM.connection, det["connectionType"] ?? dev["connectionType"]))}
            ${this.kv(t("profile.service_agreement"), this.label(ENUM.agreement, dev["serviceAgreementStatus"]))}
            ${sa["term"] ? this.kv(t("profile.term"), humanize(sa["term"])) : nothing}
            ${dealer["name"] ? this.kv(t("profile.dealer"), String(dealer["name"])) : nothing}
            ${dealer["displayPhoneNumber"] ? this.kv(t("profile.dealer_phone"), String(dealer["displayPhoneNumber"])) : nothing}
          </div>
        </div>
      </div>
      ${this.renderPeripherals(gen)}
    </div>`;
  }

  private renderPeripherals(gen: Generator): TemplateResult | typeof nothing {
    const t = this.t;
    const canAct = gen.available && !this.connectionError && gen.derived.is_connected;
    const blocks: Array<[string, Record<string, unknown> | undefined, boolean]> = [
      [t("profile.load_module"), gen.details.loadShed as Record<string, unknown> | undefined, false],
      [t("profile.pim"), gen.details.pim as Record<string, unknown> | undefined, false],
      [t("profile.transfer_switch"), gen.details.ats, true],
    ];
    const present = blocks.filter(([, block]) => block && Object.keys(block).length);
    if (!present.length) return nothing;
    return html`<div class="grid-2">
      ${present.map(([name, block, isSwitch]) => {
        const params = (block!["parameters"] as PeripheralParam[] | undefined) || [];
        const editable = canAct && block!["isConnected"] !== false;
        return html`<div class="card">
          <h2 class="card-title">${name}${"isConnected" in block! ? html` <span class="pill">${block!["isConnected"] ? t("profile.connected") : t("profile.offline")}</span>` : nothing}</h2>
          ${params.length
            ? html`<div class="params">${params.map((p) => this.renderParam(p, editable))}</div>`
            : isSwitch
              ? html`<div class="kv">
                  ${this.kv(t("profile.model"), block!["modelNo"] ?? "—")}
                  ${this.kv(t("profile.serial"), block!["serialNumber"] ?? "—")}
                  ${this.kv(t("profile.position"), this.label(ENUM.atsPosition, block!["powerSource"]))}
                </div>`
              : html`<p class="hint">${t("profile.no_parameters")}</p>`}
        </div>`;
      })}
    </div>`;
  }

  /** One load-module or PIM setting: a switch for on/off values, and an editor for the rest. */
  private renderParam(param: PeripheralParam, editable: boolean): TemplateResult {
    const name = String(param.displayName ?? `#${param.definitionId}`);
    const writable = editable && !param.isReadOnly && param.definitionId !== undefined;
    const value = param.value;
    return html`<div class="param">
      <span class="key">${name}</span>
      ${writable && typeof value === "boolean"
        ? html`<input type="checkbox" aria-label=${name} .checked=${live(value)} ?disabled=${this.busy}
            @change=${(e: Event) => this.setParam(param, (e.target as HTMLInputElement).checked)} />`
        : html`<span class="val">${this.paramValue(value)}</span>`}
      ${writable
        ? html`<button class="icon-button small" title=${this.t("profile.edit", { name })} aria-label=${this.t("profile.edit", { name })}
            ?disabled=${this.busy} @click=${() => this.openEdit(param, name)}>${icon(mdiPencil)}</button>`
        : nothing}
    </div>`;
  }

  private renderEdit(): TemplateResult | typeof nothing {
    const editing = this.editing;
    if (!editing) return nothing;
    const t = this.t;
    const numeric = typeof editing.value === "number";
    return html`<div class="scrim" @click=${this.closeEdit} @keydown=${this.onEditKey}>
      <form class="dialog" role="dialog" aria-modal="true" aria-labelledby="edit-title" novalidate
        @click=${(e: Event) => e.stopPropagation()} @submit=${this.saveEdit}>
        <h2 id="edit-title">${t("edit.title")}</h2>
        <div class="field">
          <label for="edit-name">${t("edit.name")}</label>
          <input id="edit-name" type="text" maxlength="64" autocomplete="off" .value=${editing.name} />
        </div>
        ${numeric || typeof editing.value === "string"
          ? html`<div class="field">
              <label for="edit-value">${t("edit.value")}</label>
              <input id="edit-value" type=${numeric ? "number" : "text"} step="any" maxlength="255" autocomplete="off"
                .value=${String(editing.value)} />
            </div>`
          : nothing}
        <div class="btn-row end">
          <button type="button" class="action ghost" @click=${this.closeEdit}>${t("common.cancel")}</button>
          <button type="submit" class="action">${t("edit.save")}</button>
        </div>
      </form>
    </div>`;
  }

  private renderDiagnostics(gen: Generator): TemplateResult {
    const t = this.t;
    const f = this.fmt;
    const account = this.account(gen.entry_id);
    const percent = (value: unknown) => {
      const text = fmtNumber(value, f);
      return text === null ? null : `${text}%`;
    };
    const autoUpdate = gen.details["autoFirmwareUpdateEnabled"];
    const rows: Array<[string, unknown]> = [
      [t("diagnostics.connected"), gen.derived.is_connected ? t("common.yes") : t("common.no")],
      [t("diagnostics.device_ip"), gen.derived.ip_address],
      [t("diagnostics.mac"), gen.derived.mac_address],
      [t("diagnostics.uptime"), percent(gen.device["uptimePercent"])],
      [t("diagnostics.last_connected"), fmtDateTime(gen.device["lastConnectedTimestamp"], f)],
      [t("diagnostics.parameters_updated"), fmtRelative(gen.device["latestParameterUpdateTimestamp"], f)],
      [t("diagnostics.cellular_status"), this.label(ENUM.cellular, gen.details["cellularDataStatus"])],
      [t("diagnostics.cellular_used"), percent(gen.details["cellularDataPercentage"])],
      [t("diagnostics.auto_update"), typeof autoUpdate === "boolean" ? this.paramValue(autoUpdate) : null],
      [t("diagnostics.details_refreshed"), fmtRelative(gen.details_updated, f)],
      [t("diagnostics.feeds_refreshed"), fmtRelative(gen.feeds_updated, f)],
      [t("diagnostics.account"), account?.last_update_success === false ? t("diagnostics.account_failed") : t("diagnostics.account_ok")],
    ];
    return html`<div class="section">
      <div class="card">
        <h2 class="card-title">${t("diagnostics.title")}</h2>
        <div class="kv">${rows.filter(([, v]) => v !== null && v !== undefined && v !== "").map(([k, v]) => this.kv(k, v))}</div>
      </div>
      <div class="card">
        <h2 class="card-title">${t("diagnostics.entities")}</h2>
        <p class="hint">${t("diagnostics.entities_text", { count: fmtNumber(Object.keys(gen.entities).length, f) ?? "0" })}</p>
        ${gen.ha_device_id
          ? html`<div class="btn-row spaced">${this.link(`/config/devices/device/${gen.ha_device_id}`, t("diagnostics.open_device"), "action ghost")}</div>`
          : nothing}
      </div>
    </div>`;
  }

  private renderConfirm(): TemplateResult | typeof nothing {
    const confirm = this.confirm;
    if (!confirm) return nothing;
    return html`<div class="scrim" @click=${this.closeConfirm} @keydown=${this.onConfirmKey}>
      <div class="dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-text"
        @click=${(e: Event) => e.stopPropagation()}>
        <h2 id="confirm-title">${confirm.title}</h2>
        <p id="confirm-text">${confirm.text}</p>
        <div class="btn-row end">
          <button id="confirm-cancel" class="action ghost" @click=${this.closeConfirm}>${this.t("common.cancel")}</button>
          <button id="confirm-ok" class=${`action ${confirm.danger ? "danger" : ""}`}
            @click=${() => { this.confirm = null; confirm.run(); }}>${confirm.action}</button>
        </div>
      </div>
    </div>`;
  }

  // ---- small render helpers ----
  private kv(key: string, value: unknown): TemplateResult {
    const text = value === null || value === undefined || value === "" ? "—" : String(value);
    return html`<div class="key">${key}</div><div class="val">${text}</div>`;
  }

  /** A link into Home Assistant that navigates in place (and still opens in a new tab). */
  private link(path: string, text: string, classes: string): TemplateResult {
    return html`<a class=${classes} href=${path} @click=${(e: MouseEvent) => this.navigate(e, path)}>${icon(mdiOpenInNew)} ${text}</a>`;
  }

  private paramValue(value: unknown): string {
    if (typeof value === "boolean") return value ? this.t("common.on") : this.t("common.off");
    if (value === null || value === undefined) return "—";
    return typeof value === "number" ? fmtNumber(value, this.fmt, Number.isInteger(value) ? 0 : 1) ?? "—" : String(value);
  }

  private statusText(gen: Generator, vstate: VisualState): string {
    if (vstate === "running") {
      return this.t(gen.derived.utility_present === false ? "status.running_outage" : "status.running");
    }
    if (vstate !== "standby") return this.t(STATUS_TEXT[vstate]);
    if (gen.derived.ready_to_run) return this.t("status.ready");
    return this.label(ENUM.status, gen.device["status"]) || this.t("status.standby");
  }

  private chipColor(vstate: VisualState): string {
    if (vstate === "offline") return "var(--rk-muted)";
    if (vstate === "fault" || vstate === "estop") return "var(--rk-bad)";
    if (vstate === "exercising") return "var(--rk-util)";
    return "var(--rk-ok)";
  }

  // ---- interactions ----
  private toggleMenu(): void {
    this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }));
  }

  private refresh(): void {
    if (this.connectionError) void this.subscribe();
    else void this.call("refresh", {}, "toast.refreshed");
  }

  private navigate(event: MouseEvent, path: string): void {
    // Let the browser handle new-tab clicks; otherwise move within Home Assistant's own page.
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    history.pushState(null, "", path);
    window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
  }

  private onPick(e: Event): void {
    this.selected = (e.target as HTMLSelectElement).value;
    this.tab = "overview";
    this.eventLimit = PAGE;
    this.notificationLimit = PAGE;
  }

  private onTabKey(e: KeyboardEvent): void {
    const index = TABS.indexOf(this.tab);
    const next = e.key === "ArrowRight" ? index + 1 : e.key === "ArrowLeft" ? index - 1
      : e.key === "Home" ? 0 : e.key === "End" ? TABS.length - 1 : null;
    if (next === null) return;
    e.preventDefault();
    this.tab = TABS[(next + TABS.length) % TABS.length];
    void this.updateComplete.then(() => this.field<HTMLButtonElement>(`tab-${this.tab}`)?.focus());
  }

  private ask(confirm: Confirm): void {
    this.rememberFocus();
    this.confirm = confirm;
  }

  private askStart(): void {
    this.ask({
      title: this.t("confirm.start.title"), text: this.t("confirm.start.text"),
      action: this.t("confirm.start.action"), danger: false,
      run: () => void this.call("start_exercise", {}, "toast.exercise_started"),
    });
  }

  private askDelete(): void {
    this.ask({
      title: this.t("confirm.delete.title"), text: this.t("confirm.delete.text"),
      action: this.t("confirm.delete.action"), danger: true,
      run: () => void this.call("delete_exercise_schedule", {}, "toast.schedule_deleted"),
    });
  }

  private closeConfirm(): void {
    this.confirm = null;
  }

  private onConfirmKey(e: KeyboardEvent): void {
    if (e.key === "Escape") this.closeConfirm();
    else this.keepFocusInDialog(e);
  }

  /** Tab and Shift+Tab cycle through the open dialog's controls instead of leaving it. */
  private keepFocusInDialog(e: KeyboardEvent): void {
    if (e.key !== "Tab") return;
    const controls = [...this.renderRoot.querySelectorAll<HTMLElement>(".dialog input, .dialog button")];
    if (!controls.length) return;
    e.preventDefault();
    const at = controls.indexOf((this.renderRoot as ShadowRoot).activeElement as HTMLElement);
    controls[(at + (e.shiftKey ? -1 : 1) + controls.length) % controls.length].focus();
  }

  private rememberFocus(): void {
    this.restoreFocus = this.renderRoot instanceof ShadowRoot ? this.renderRoot.activeElement as HTMLElement | null : null;
  }

  private openEdit(param: PeripheralParam, name: string): void {
    this.rememberFocus();
    this.editing = { definitionId: param.definitionId, name, value: param.value };
  }

  private closeEdit(): void {
    this.editing = null;
  }

  private onEditKey(e: KeyboardEvent): void {
    if (e.key === "Escape") this.closeEdit();
    else this.keepFocusInDialog(e);
  }

  private async setParam(param: PeripheralParam, value: unknown): Promise<void> {
    await this.call("set_peripheral_value", { definition_id: String(param.definitionId), value }, "toast.setting_saved");
    // Put the switch back if the write failed and no new snapshot corrects it.
    this.requestUpdate();
  }

  private async saveEdit(e: Event): Promise<void> {
    e.preventDefault();
    const editing = this.editing;
    if (!editing) return;
    const name = this.field<HTMLInputElement>("edit-name")?.value.trim() ?? "";
    if (!name) {
      this.showToast(this.t("toast.name_required"), true);
      return;
    }
    const input = this.field<HTMLInputElement>("edit-value");
    let value: unknown = editing.value;
    if (input) {
      value = typeof editing.value === "number" ? Number(input.value) : input.value;
      if (input.value.trim() === "" || (typeof value === "number" && !Number.isFinite(value))) {
        this.showToast(this.t("toast.value_invalid"), true);
        return;
      }
    }
    this.editing = null;
    const definition_id = String(editing.definitionId);
    if (name !== editing.name && !(await this.call("rename_peripheral", { definition_id, name }, "toast.setting_saved"))) return;
    if (value !== editing.value) await this.call("set_peripheral_value", { definition_id, value }, "toast.setting_saved");
  }

  private field<T extends HTMLElement>(id: string): T | null {
    return this.renderRoot.querySelector<T>(`#${id}`);
  }

  private async saveSchedule(): Promise<void> {
    for (const input of this.renderRoot.querySelectorAll<HTMLInputElement>(".field input")) {
      if (!input.reportValidity()) return;
    }
    const freq = this.field<HTMLSelectElement>("freq")?.value;
    const mode = this.field<HTMLSelectElement>("mode")?.value;
    const dur = this.field<HTMLInputElement>("dur")?.value;
    const next = this.field<HTMLInputElement>("next")?.value;
    const data: Record<string, unknown> = {};
    if (freq) data.frequency = freq;
    if (mode) data.mode = mode;
    if (dur) data.duration = Number(dur);
    if (next) {
      const timestamp = fromInputValue(next, this.fmt);
      if (!timestamp) {
        this.showToast(this.t("toast.invalid_next_start"), true);
        return;
      }
      data.next_start = timestamp.toISOString();
    }
    await this.call("set_exercise_schedule", data, "toast.schedule_saved");
  }

  private async saveNote(): Promise<void> {
    const el = this.field<HTMLTextAreaElement>("note");
    const note = el?.value.trim();
    if (!note) {
      this.showToast(this.t("toast.note_required"), true);
      return;
    }
    if (await this.call("add_maintenance_note", { note }, "toast.note_added") && el) el.value = "";
  }

  private async toggleNotify(gen: Generator, key: string, enabled: boolean): Promise<void> {
    if (this.busy) return;
    const account = this.account(gen.entry_id);
    const entityId = account?.notification_entities?.[key];
    if (!entityId) {
      this.showToast(this.t("toast.notify_unavailable"), true);
      return;
    }
    this.busy = true;
    try {
      await this.hass!.callService("switch", enabled ? "turn_on" : "turn_off", { entity_id: entityId });
    } catch (err) {
      this.showToast(errorMessage(err, this.t("toast.setting_failed")), true);
    } finally {
      this.busy = false;
      // Restore the server value even when no new snapshot was emitted after a failure.
      this.requestUpdate();
    }
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "rehlko-energy-panel": RehlkoEnergyPanel;
  }
}
