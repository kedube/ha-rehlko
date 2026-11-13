// Exercise the exact production bundle Home Assistant serves, with no cloud credentials.
import "../../custom_components/rehlko_energy/www/rehlko-energy-panel.js";
import type { RehlkoEnergyPanel } from "../src/rehlko-energy-panel";
import type { HomeAssistant, Snapshot } from "../src/types";
import { sampleGenerator, sampleSnapshot } from "../test/fixtures";

type Tree = { [key: string]: string | Tree };

// The integration's own translation files stand in for Home Assistant's `hass.localize`,
// so the preview shows enum values in each language exactly as the real panel does.
const TRANSLATIONS = import.meta.glob<Tree>(
  "../../custom_components/rehlko_energy/translations/*.json", { eager: true, import: "default" },
);
const LANGUAGES: Record<string, Record<string, string>> = {};
function flatten(tree: Tree, prefix: string, out: Record<string, string>): Record<string, string> {
  for (const [key, value] of Object.entries(tree)) {
    if (typeof value === "string") out[`${prefix}.${key}`] = value;
    else flatten(value, `${prefix}.${key}`, out);
  }
  return out;
}
for (const [path, tree] of Object.entries(TRANSLATIONS)) {
  LANGUAGES[path.replace(/^.*\/|\.json$/g, "")] = flatten(tree, "component.rehlko_energy", {});
}

const panel = document.querySelector("rehlko-energy-panel") as RehlkoEnergyPanel;
const params = new URLSearchParams(location.search);
const control = (id: string) => document.querySelector<HTMLSelectElement>(`#${id}`)!;

const languageSelect = control("lang");
for (const language of Object.keys(LANGUAGES).sort()) languageSelect.add(new Option(language, language));
languageSelect.value = "en";
for (const id of ["state", "model", "theme", "lang", "units"]) {
  const wanted = params.get(id);
  const select = control(id);
  const match = wanted && [...select.options].find((o) => o.value.toLowerCase() === wanted.toLowerCase());
  if (match) select.value = match.value;
}
if (params.get("bar") === "0") document.querySelector(".demo")!.classList.add("hidden");
panel.narrow = params.get("narrow") === "1";

let send: ((snapshot: Snapshot) => void) | undefined;
let snapshot = sampleSnapshot();
const connection: HomeAssistant["connection"] = {
  async subscribeMessage<T>(callback: (message: T) => void) {
    send = callback as (snapshot: Snapshot) => void;
    send(snapshot);
    return () => { send = undefined; };
  },
  async sendMessagePromise<T>() { return {} as T; },
};

function hass(): HomeAssistant {
  const language = control("lang").value;
  const strings = { ...LANGUAGES.en, ...LANGUAGES[language] };
  const metric = control("units").value === "Metric";
  return {
    states: {}, language, connection,
    locale: { language, number_format: "language", time_format: "language", time_zone: "local" },
    config: {
      time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      unit_system: metric ? { temperature: "°C", pressure: "Pa" } : { temperature: "°F", pressure: "psi" },
    },
    dockedSidebar: "docked",
    localize: (key: string) => strings[key] ?? "",
    async callService() { throw { message: "Preview only — no action was sent." }; },
    async callWS<T>() { return snapshot as T; },
  };
}

const ago = (minutes: number) => new Date(Date.now() - minutes * 6e4).toISOString();

function demoGenerator(state: string, model: string) {
  const generator = sampleGenerator();
  Object.assign(generator.device, {
    model, modelDisplayName: model, serialNumber: "DEMO-001", controllerType: "RDC2", firmwareVersion: "3.14",
    serviceAgreementStatus: "Active", connectionType: "KohlerWifi", uptimePercent: 99,
    lastConnectedTimestamp: ago(1), latestParameterUpdateTimestamp: ago(12),
    lastMaintenanceTimestamp: ago(60 * 24 * 150), nextMaintenanceTimestamp: new Date(Date.now() + 864e5 * 215).toISOString(),
    maintenancePeriodDays: 365, deviceIpAddress: "[::ffff:192.0.2.25]:42636", macAddress: "02:00:00:00:00:01",
    address: { address1: "1 Example Way", city: "Springfield", postalCode: "00000" },
    dealerOrgs: [{ name: "Example Power Systems", displayPhoneNumber: "(555) 010-0000" }],
  });
  Object.assign(generator.details, {
    switchState: "Auto", engineState: "Standby", fuelType: "NaturalGas", coolingType: "Air",
    setOutputVoltageV: 240, engineFrequencyHz: 0, engineOilPressurePsi: 0, engineCoolantTempF: 68,
    lubeOilTempF: 70, lastRanTimestamp: ago(60 * 24 * 6), runtimeSinceLastMaintenanceHours: 14.5,
    controllerClockTimestamp: ago(0), autoFirmwareUpdateEnabled: true, cellularDataStatus: "Active",
    loadShed: { isConnected: true, parameters: [
      { definitionId: 1, displayName: "Air conditioner", value: true },
      { definitionId: 2, displayName: "Water heater", value: false },
      { definitionId: 3, displayName: "Restart delay", value: 30 },
      { definitionId: 4, displayName: "Module", value: "LM-200", isReadOnly: true },
    ] },
    ats: { serialNumber: "ATS-0001", modelNo: "RXT-JFNC-0200A", powerSource: "Utility" },
  });
  generator.details.exercise = {
    ...generator.details.exercise, lastStartTimestamp: ago(60 * 24 * 6),
    nextStartTimestamp: new Date(Date.now() + 864e5).toISOString(),
  };
  generator.events = [
    { id: 4, name: "Exercise ended", level: "Status", timestamp: ago(60 * 24 * 6 - 20), type: "Event" },
    { id: 3, name: "Exercise started", level: "Status", timestamp: ago(60 * 24 * 6) },
    { id: 2, name: "Low battery voltage", level: "Warning", timestamp: ago(60 * 24 * 19) },
    { id: 1, name: "Utility power restored", level: "Notice", timestamp: ago(60 * 24 * 40) },
  ];
  generator.notifications = [
    { id: 2, type: "ExerciseEndedNotice", message: "Home generator finished its exercise.", timestamp: ago(60 * 24 * 6 - 20) },
    { id: 1, type: "Warning", message: "Home generator reported low battery voltage.", timestamp: ago(60 * 24 * 19) },
  ];
  generator.maintenance_notes = [
    { id: 1, timestamp: ago(60 * 24 * 150), contents: "Annual service: oil, filter and spark plugs.", authorIsDealer: true, dealerAuthor: "Example Power Systems" },
  ];
  generator.entities = Object.fromEntries(Array.from({ length: 64 }, (_, i) => [`sensor.demo_${i}`, `sensor.demo_${i}`]));
  generator.feeds_updated = ago(1);
  generator.derived.ip_address = "192.0.2.25";

  if (state === "Running" || state === "Exercising") {
    const exercising = state === "Exercising";
    Object.assign(generator.device, { status: exercising ? "RunningExercise" : "Running" });
    Object.assign(generator.derived, {
      is_running: true, ready_to_run: false, is_exercising: exercising,
      utility_present: exercising, on_generator_power: !exercising,
    });
    Object.assign(generator.details, {
      engineSpeedRpm: 3600, generatorLoadW: exercising ? 0 : 5400, engineFrequencyHz: 60,
      engineState: exercising ? "PerformingUnloadedFullSpeedExercise" : "Running",
      generatorVoltageAvgV: 241, utilityVoltageV: exercising ? 240 : 0,
      powerSource: exercising ? "Utility" : "Generator", engineOilPressurePsi: 52, engineCoolantTempF: 188,
    });
  } else if (state === "Offline") {
    generator.derived.is_connected = false;
    generator.device.status = "Offline";
  } else if (state === "Stale") {
    generator.available = false;
  } else if (state === "Fault") {
    generator.device.status = "Shutdown";
    generator.derived.ready_to_run = false;
    generator.alerts = [{ id: 9, name: "Low oil pressure shutdown", level: "Shutdown", isCriticalFault: true, timestamp: ago(42) }];
  }
  return generator;
}

function applyTheme(): void {
  const dark = control("theme").value === "Dark";
  const colors = dark
    ? { bg: "#111416", card: "#1c1f22", fg: "#e4e8eb", muted: "#a0a8af", divider: "#343b41" }
    : { bg: "#f3f4f6", card: "#fff", fg: "#1a1a1a", muted: "#5f666d", divider: "#e0e0e0" };
  const variables = {
    "primary-background-color": colors.bg, "card-background-color": colors.card,
    "primary-text-color": colors.fg, "secondary-text-color": colors.muted, "divider-color": colors.divider,
  };
  for (const [name, value] of Object.entries(variables)) document.documentElement.style.setProperty(`--${name}`, value);
  document.documentElement.style.colorScheme = dark ? "dark" : "light";
}

function update(): void {
  const state = control("state").value;
  snapshot = sampleSnapshot(state === "Empty" ? [] : [demoGenerator(state, control("model").value)]);
  snapshot.accounts[0].notification_settings = {
    sendShutdowns: true, sendWarnings: true, sendGeneratorRunningNotices: true, sendMaintenanceNotices: false,
  };
  snapshot.accounts[0].notification_entities = {
    sendShutdowns: "switch.demo_shutdowns", sendWarnings: "switch.demo_warnings",
    sendGeneratorRunningNotices: "switch.demo_running", sendMaintenanceNotices: "switch.demo_maintenance",
  };
  applyTheme();
  document.documentElement.lang = control("lang").value;
  panel.hass = hass();
  send?.(snapshot);
}

// In a real Home Assistant shell these events open its sidebar and change its page.
panel.addEventListener("hass-toggle-menu", () => alert("Home Assistant opens its sidebar here."));
window.addEventListener("location-changed", () => alert(`Home Assistant opens ${location.pathname} here.`));
for (const id of ["state", "model", "theme", "lang", "units"]) control(id).addEventListener("change", update);
update();

// For screenshots: ?tab=controls opens a tab, and &press=<button id, text or label> then clicks it.
function whenReady<T>(find: () => T | null | undefined, then: (found: T) => void, tries = 200): void {
  const found = find();
  if (found) then(found);
  else if (tries > 0) requestAnimationFrame(() => whenReady(find, then, tries - 1));
}
const root = () => panel.shadowRoot;
const tab = params.get("tab");
const press = params.get("press");
whenReady(() => root()?.querySelector<HTMLButtonElement>(`#tab-${tab ?? "overview"}`), (button) => {
  button.click();
  if (!press) return;
  whenReady(
    () => [...(root()?.querySelectorAll<HTMLButtonElement>("#tabpanel button") ?? [])]
      .find((candidate) => candidate.id === press || candidate.textContent?.includes(press)
        || candidate.getAttribute("aria-label")?.includes(press)),
    (target) => target.click(),
  );
});
