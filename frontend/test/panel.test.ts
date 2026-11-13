import { afterEach, describe, expect, it, vi } from "vitest";
import { RehlkoEnergyPanel } from "../src/rehlko-energy-panel";
import es from "../src/locales/es.json";
import type { Generator, HomeAssistant, Snapshot } from "../src/types";
import { sampleGenerator, sampleSnapshot } from "./fixtures";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

function setup(snapshot = sampleSnapshot()) {
  let send!: (value: Snapshot) => void;
  const unsub = vi.fn();
  const subscribeMessage = vi.fn(async (cb: (value: Snapshot) => void): Promise<() => void> => {
    send = cb;
    cb(snapshot);
    return unsub;
  });
  const callService = vi.fn(async () => {});
  const hass = { states: {}, connection: { subscribeMessage }, callService } as unknown as HomeAssistant;
  const panel = new RehlkoEnergyPanel();
  panel.hass = hass;
  return { panel, hass, unsub, subscribeMessage, callService, send: (s: Snapshot) => send(s) };
}

async function settle(panel: RehlkoEnergyPanel) {
  await Promise.resolve();
  await panel.updateComplete;
  await Promise.resolve();
}

function clickTab(panel: RehlkoEnergyPanel, text: string) {
  const tab = [...panel.shadowRoot!.querySelectorAll<HTMLButtonElement>("[role=tab]")]
    .find((button) => button.textContent === text)!;
  tab.click();
}

function button(panel: RehlkoEnergyPanel, text: string): HTMLButtonElement {
  return [...panel.shadowRoot!.querySelectorAll<HTMLButtonElement>("button")]
    .find((candidate) => candidate.textContent!.includes(text))!;
}

async function openControls(panel: RehlkoEnergyPanel) {
  document.body.append(panel);
  await settle(panel);
  clickTab(panel, "Controls");
  await settle(panel);
}

afterEach(() => {
  document.body.replaceChildren();
  vi.useRealTimers();
});

describe("panel lifecycle", () => {
  it("subscribes once across hass updates and releases subscriptions", async () => {
    const { panel, hass, subscribeMessage, unsub } = setup();
    document.body.append(panel);
    await settle(panel);
    panel.hass = { ...hass };
    await settle(panel);
    expect(subscribeMessage).toHaveBeenCalledTimes(1);
    expect(panel.shadowRoot!.textContent).toContain("Home generator");
    panel.remove();
    expect(unsub).toHaveBeenCalledTimes(1);
  });

  it("cancels a subscription that finishes after disconnection", async () => {
    const { panel, subscribeMessage } = setup();
    const pending = deferred<() => void>();
    subscribeMessage.mockReturnValue(pending.promise);
    document.body.append(panel);
    await settle(panel);
    panel.remove();
    const unsubscribe = vi.fn();
    pending.resolve(unsubscribe);
    await settle(panel);
    expect(unsubscribe).toHaveBeenCalledOnce();
  });

  it("shows connection errors and retries instead of claiming there is no integration", async () => {
    vi.useFakeTimers();
    const { panel, subscribeMessage } = setup();
    subscribeMessage.mockRejectedValue({ message: "Administrator access required" });
    document.body.append(panel);
    await settle(panel);
    expect(panel.shadowRoot!.textContent).toContain("Administrator access required");
    expect(panel.shadowRoot!.textContent).not.toContain("Add the Rehlko");
    await vi.advanceTimersByTimeAsync(5000);
    expect(subscribeMessage).toHaveBeenCalledTimes(2);
    panel.remove();
    await vi.advanceTimersByTimeAsync(5000);
    expect(subscribeMessage).toHaveBeenCalledTimes(2);
  });

  it("replaces the subscription when Home Assistant changes connections", async () => {
    const first = setup();
    const second = setup();
    document.body.append(first.panel);
    await settle(first.panel);
    first.panel.hass = second.hass;
    await settle(first.panel);
    expect(first.unsub).toHaveBeenCalledOnce();
    expect(second.subscribeMessage).toHaveBeenCalledOnce();
  });
});

describe("product image rendering", () => {
  it("renders the 26RCA photograph with its original aspect ratio", async () => {
    const { panel } = setup();
    document.body.append(panel);
    await settle(panel);
    const image = panel.shadowRoot!.querySelector<HTMLImageElement>(".generator-photo")!;
    expect(image.alt).toContain("KOHLER RCA");
    expect(image.getAttribute("width")).toBe("1000");
    expect(image.getAttribute("height")).toBe("626");
    expect(panel.shadowRoot!.querySelector("figcaption")!.textContent).toBe("KOHLER 26RCA");
    expect(panel.shadowRoot!.querySelector("svg.gen")).toBeNull();
  });

  it("updates the enclosure image when selecting a different generator", async () => {
    const { panel } = setup(sampleSnapshot([
      sampleGenerator(), sampleGenerator({ device_id: 2, device: { model: "48RCLC" } }),
    ]));
    document.body.append(panel);
    await settle(panel);
    const before = panel.shadowRoot!.querySelector<HTMLImageElement>(".generator-photo")!.src;
    const picker = panel.shadowRoot!.querySelector<HTMLSelectElement>(".picker")!;
    picker.value = "account-1:2";
    picker.dispatchEvent(new Event("change"));
    await settle(panel);
    const image = panel.shadowRoot!.querySelector<HTMLImageElement>(".generator-photo")!;
    expect(image.src).not.toBe(before);
    expect(image.alt).toContain("48RCLC");
    expect(panel.shadowRoot!.querySelector("figcaption")!.textContent).toBe("KOHLER 48RCLC");
  });
});

describe("panel controls", () => {
  it("retains maintenance notes and displays structured service errors", async () => {
    const { panel, callService } = setup();
    document.body.append(panel);
    await settle(panel);
    clickTab(panel, "Controls");
    await settle(panel);
    const note = panel.shadowRoot!.querySelector<HTMLTextAreaElement>("#note")!;
    note.value = "Changed the oil";
    callService.mockRejectedValue({ message: "Cloud unavailable" });
    [...panel.shadowRoot!.querySelectorAll<HTMLButtonElement>("button")]
      .find((button) => button.textContent!.includes("Add note"))!.click();
    await settle(panel);
    expect(note.value).toBe("Changed the oil");
    expect(panel.shadowRoot!.textContent).toContain("Cloud unavailable");
  });

  it("disables remote exercise on stale readings", async () => {
    const { panel } = setup(sampleSnapshot([sampleGenerator({ available: false })]));
    document.body.append(panel);
    await settle(panel);
    expect(panel.shadowRoot!.textContent).toContain("last reported readings");
    clickTab(panel, "Controls");
    await settle(panel);
    const start = [...panel.shadowRoot!.querySelectorAll<HTMLButtonElement>("button")]
      .find((button) => button.textContent!.includes("Start exercise now"))!;
    expect(start.disabled).toBe(true);
  });

  it("supports generators with the same cloud id on different accounts", async () => {
    const { panel } = setup(sampleSnapshot([
      sampleGenerator(), sampleGenerator({ entry_id: "account-2", name: "Other generator" }),
    ]));
    document.body.append(panel);
    await settle(panel);
    const picker = panel.shadowRoot!.querySelector<HTMLSelectElement>(".picker")!;
    picker.value = "account-2:1";
    picker.dispatchEvent(new Event("change"));
    await settle(panel);
    expect(panel.shadowRoot!.querySelector("h1")!.textContent).toBe("Other generator");
  });

  it("provides Home Assistant's sidebar toggle where the sidebar is hidden", async () => {
    const { panel } = setup();
    const toggle = vi.fn();
    panel.addEventListener("hass-toggle-menu", toggle);
    document.body.append(panel);
    await settle(panel);
    // On a wide screen the sidebar is already showing, as in Home Assistant's own panels.
    expect(panel.shadowRoot!.querySelector('[aria-label="Open sidebar"]')).toBeNull();
    panel.narrow = true;
    await settle(panel);
    panel.shadowRoot!.querySelector<HTMLButtonElement>('[aria-label="Open sidebar"]')!.click();
    expect(toggle).toHaveBeenCalledOnce();
  });

  it("asks before starting the engine, and starts only on confirmation", async () => {
    const { panel, callService } = setup();
    await openControls(panel);
    button(panel, "Start exercise now").click();
    await settle(panel);
    const dialog = panel.shadowRoot!.querySelector('[role="alertdialog"]')!;
    expect(dialog.textContent).toContain("Start an exercise now?");
    expect(callService).not.toHaveBeenCalled();
    panel.shadowRoot!.querySelector<HTMLButtonElement>("#confirm-cancel")!.click();
    await settle(panel);
    expect(panel.shadowRoot!.querySelector('[role="alertdialog"]')).toBeNull();
    expect(callService).not.toHaveBeenCalled();

    button(panel, "Start exercise now").click();
    await settle(panel);
    panel.shadowRoot!.querySelector<HTMLButtonElement>("#confirm-ok")!.click();
    await settle(panel);
    expect(callService).toHaveBeenCalledWith("rehlko_energy", "start_exercise", { device_id: "ha-device-1" });
    expect(panel.shadowRoot!.querySelector('[role="alertdialog"]')).toBeNull();
  });

  it("asks before deleting the schedule and closes the question on Escape", async () => {
    const { panel, callService } = setup();
    await openControls(panel);
    button(panel, "Delete schedule").click();
    await settle(panel);
    const scrim = panel.shadowRoot!.querySelector(".scrim")!;
    expect(scrim.textContent).toContain("Delete the exercise schedule?");
    scrim.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await settle(panel);
    expect(panel.shadowRoot!.querySelector(".scrim")).toBeNull();
    expect(callService).not.toHaveBeenCalled();
  });

  it("sends the schedule as edited, with the next start as an instant", async () => {
    const { panel, callService } = setup();
    await openControls(panel);
    const root = panel.shadowRoot!;
    root.querySelector<HTMLSelectElement>("#freq")!.value = "Monthly";
    root.querySelector<HTMLInputElement>("#dur")!.value = "30";
    root.querySelector<HTMLInputElement>("#next")!.value = "2026-12-01T09:30";
    button(panel, "Save schedule").click();
    await settle(panel);
    expect(callService).toHaveBeenCalledWith("rehlko_energy", "set_exercise_schedule", {
      device_id: "ha-device-1", frequency: "Monthly", mode: "Unloaded", duration: 30,
      next_start: new Date(2026, 11, 1, 9, 30).toISOString(),
    });
    expect(root.textContent).toContain("Schedule saved.");
  });

  it("moves between tabs with the arrow keys", async () => {
    const { panel } = setup();
    document.body.append(panel);
    await settle(panel);
    const tablist = panel.shadowRoot!.querySelector('[role="tablist"]')!;
    const selected = () => panel.shadowRoot!.querySelector('[role="tab"][aria-selected="true"]')!;
    tablist.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    await settle(panel);
    expect(selected().id).toBe("tab-controls");
    expect(selected().getAttribute("tabindex")).toBe("0");
    tablist.dispatchEvent(new KeyboardEvent("keydown", { key: "End", bubbles: true }));
    await settle(panel);
    expect(selected().id).toBe("tab-diagnostics");
    tablist.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    await settle(panel);
    expect(selected().id).toBe("tab-overview");
    expect(panel.shadowRoot!.querySelector('[role="tabpanel"]')!.getAttribute("aria-labelledby")).toBe("tab-overview");
  });

  it("shows long activity logs a page at a time", async () => {
    const events = Array.from({ length: 120 }, (_, id) => ({ id, name: `Event ${id}`, level: "Status" }));
    const { panel } = setup(sampleSnapshot([sampleGenerator({ events })]));
    document.body.append(panel);
    await settle(panel);
    clickTab(panel, "Activity");
    await settle(panel);
    const rows = () => panel.shadowRoot!.querySelectorAll(".list-item").length;
    expect(rows()).toBe(50);
    button(panel, "Show more").click();
    await settle(panel);
    expect(rows()).toBe(100);
    button(panel, "Show more").click();
    await settle(panel);
    expect(rows()).toBe(120);
    expect(button(panel, "Show more")).toBeUndefined();
  });

  it("links to the generator's device page without leaving Home Assistant", async () => {
    const { panel } = setup();
    const moved = vi.fn();
    window.addEventListener("location-changed", moved);
    document.body.append(panel);
    await settle(panel);
    clickTab(panel, "Diagnostics");
    await settle(panel);
    const link = panel.shadowRoot!.querySelector<HTMLAnchorElement>('a[href="/config/devices/device/ha-device-1"]')!;
    link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, button: 0 }));
    expect(moved).toHaveBeenCalledOnce();
    expect(location.pathname).toBe("/config/devices/device/ha-device-1");
    window.removeEventListener("location-changed", moved);
  });

  it("shows the controller's address without the socket the service wraps it in", async () => {
    const generator = sampleGenerator();
    generator.device["deviceIpAddress"] = "[::ffff:192.0.2.25]:42636";
    generator.derived.ip_address = "192.0.2.25";
    const { panel } = setup(sampleSnapshot([generator]));
    document.body.append(panel);
    await settle(panel);
    clickTab(panel, "Diagnostics");
    await settle(panel);
    const values = [...panel.shadowRoot!.querySelectorAll(".kv > *")].map((cell) => cell.textContent?.trim());
    expect(values).toContain("192.0.2.25");
    expect(panel.shadowRoot!.textContent).not.toContain("ffff");
  });

  it("rolls notification controls back after failed service calls", async () => {
    const { panel, callService } = setup();
    document.body.append(panel);
    await settle(panel);
    clickTab(panel, "Controls");
    await settle(panel);
    const checkbox = panel.shadowRoot!.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
    callService.mockRejectedValue({ message: "Failed to save" });
    checkbox.click();
    await settle(panel);
    expect(checkbox.checked).toBe(true);
    expect(panel.shadowRoot!.textContent).toContain("Failed to save");
  });
});

describe("language and units", () => {
  it("shows the panel in the viewer's language, including regional variants", async () => {
    const { panel, hass } = setup();
    panel.hass = { ...hass, language: "en", locale: { language: "es-419" } };
    document.body.append(panel);
    await settle(panel);
    const tabs = [...panel.shadowRoot!.querySelectorAll('[role="tab"]')].map((tab) => tab.textContent);
    expect(tabs).toContain(es["tab.controls"]);
    expect(tabs).not.toContain("Controls");
    expect(panel.shadowRoot!.querySelector(".status-chip")!.textContent).toBe(es["status.ready"]);
  });

  it("switches language without resubscribing", async () => {
    const { panel, hass, subscribeMessage } = setup();
    document.body.append(panel);
    await settle(panel);
    expect(panel.shadowRoot!.querySelector("#tab-overview")!.textContent).toBe("Overview");
    panel.hass = { ...hass, language: "es" };
    await settle(panel);
    expect(panel.shadowRoot!.querySelector("#tab-overview")!.textContent).toBe(es["tab.overview"]);
    expect(subscribeMessage).toHaveBeenCalledTimes(1);
  });

  it("falls back to English for a language it has no file for", async () => {
    const { panel, hass } = setup();
    panel.hass = { ...hass, language: "xx" };
    document.body.append(panel);
    await settle(panel);
    expect(panel.shadowRoot!.querySelector("#tab-overview")!.textContent).toBe("Overview");
  });

  it("names enum values with the integration's own translations", async () => {
    const { panel, hass } = setup();
    const strings: Record<string, string> = {
      "component.rehlko_energy.entity.sensor.status.state.ready_to_run": "Listo para funcionar",
      "component.rehlko_energy.entity.select.exercise_mode.state.unloaded": "Sin carga",
      "component.rehlko_energy.entity.switch.notify_warnings.name": "Notificaciones de advertencia",
    };
    panel.hass = { ...hass, localize: (key: string) => strings[key] ?? "" };
    document.body.append(panel);
    await settle(panel);
    const text = panel.shadowRoot!.textContent!;
    expect(text).toContain("Listo para funcionar");
    expect(text).toContain("Sin carga");
    // No translation for this one: the wire value is made readable instead.
    expect(text).toContain("Weekly");
    clickTab(panel, "Controls");
    await settle(panel);
    expect(panel.shadowRoot!.querySelector(".toggle")!.textContent).toContain("Notificaciones de advertencia");
  });

  it("asks Home Assistant for the integration's translations once per language", async () => {
    const { panel, hass } = setup();
    const loadBackendTranslation = vi.fn(async () => undefined);
    panel.hass = { ...hass, language: "en", loadBackendTranslation };
    document.body.append(panel);
    await settle(panel);
    panel.hass = { ...hass, language: "en", loadBackendTranslation, states: {} };
    await settle(panel);
    expect(loadBackendTranslation).toHaveBeenCalledTimes(1);
    expect(loadBackendTranslation).toHaveBeenCalledWith("entity", "rehlko_energy");
    panel.hass = { ...hass, language: "fr", loadBackendTranslation };
    await settle(panel);
    expect(loadBackendTranslation).toHaveBeenCalledTimes(2);
  });

  it("re-renders when Home Assistant finishes loading translations", async () => {
    const { panel, hass } = setup();
    document.body.append(panel);
    await settle(panel);
    expect(panel.shadowRoot!.textContent).toContain("Unloaded");
    panel.hass = { ...hass, localize: (key: string) => (key.endsWith("exercise_mode.state.unloaded") ? "Sin carga" : "") };
    await settle(panel);
    expect(panel.shadowRoot!.textContent).toContain("Sin carga");
  });

  it("converts the API's °F and psi for metric installations", async () => {
    const generator = sampleGenerator();
    Object.assign(generator.details, { engineCoolantTempF: 212, engineOilPressurePsi: 50 });
    const { panel, hass } = setup(sampleSnapshot([generator]));
    document.body.append(panel);
    await settle(panel);
    const stats = () => [...panel.shadowRoot!.querySelectorAll(".stat .v")].map((stat) => stat.textContent);
    expect(stats()).toContain("212°F");
    expect(stats()).toContain("50psi");
    panel.hass = { ...hass, config: { unit_system: { temperature: "°C", pressure: "Pa" } } };
    await settle(panel);
    expect(stats()).toContain("100°C");
    expect(stats()).toContain("345kPa");
  });

  it("reports the generator's load only while it is running", async () => {
    const generator = sampleGenerator();
    generator.details.generatorLoadW = -5400;
    generator.derived.load_w = 5400;
    const { panel, send } = setup(sampleSnapshot([generator]));
    document.body.append(panel);
    await settle(panel);
    const labels = () => [...panel.shadowRoot!.querySelectorAll(".stat .k")].map((label) => label.textContent);
    expect(labels()).not.toContain("Load");
    generator.derived = { ...generator.derived, is_running: true, on_generator_power: true, utility_present: false };
    send(sampleSnapshot([{ ...generator }]));
    await settle(panel);
    expect(labels()).toContain("Load");
    expect(panel.shadowRoot!.querySelector(".node.home .value")!.textContent).toBe("Generator");
    expect(panel.shadowRoot!.querySelector(".wire.generator")!.classList.contains("flowing")).toBe(true);
    expect(panel.shadowRoot!.querySelector(".node.utility")!.classList.contains("down")).toBe(true);
  });
});

describe("trimmed snapshots", () => {
  it("keeps the lists the server leaves out as unchanged", async () => {
    const events = Array.from({ length: 3 }, (_, id) => ({ id, name: `Event ${id}`, level: "Status" }));
    const generator = sampleGenerator({ events, entities: { "sensor.a": "sensor.a", "sensor.b": "sensor.b" } });
    const { panel, send } = setup(sampleSnapshot([generator]));
    document.body.append(panel);
    await settle(panel);
    clickTab(panel, "Activity");
    await settle(panel);
    const rows = () => panel.shadowRoot!.querySelectorAll(".list-item").length;
    expect(rows()).toBe(3);

    // The next poll: fresh telemetry, and no feeds because they have not changed.
    const slim: Partial<Generator> = { ...generator, details: { ...generator.details, batteryVoltageV: 12.1 } };
    delete slim.events;
    delete slim.notifications;
    delete slim.maintenance_notes;
    delete slim.entities;
    send(sampleSnapshot([slim as Generator]));
    await settle(panel);
    expect(rows()).toBe(3);
    expect([...panel.shadowRoot!.querySelectorAll(".stat .v")].map((stat) => stat.textContent)).toContain("12.1V");
    clickTab(panel, "Diagnostics");
    await settle(panel);
    expect(panel.shadowRoot!.textContent).toContain("2 Home Assistant entities");

    // A changed list replaces the old one.
    send(sampleSnapshot([{ ...(slim as Generator), events: events.slice(0, 1) }]));
    await settle(panel);
    clickTab(panel, "Activity");
    await settle(panel);
    expect(rows()).toBe(1);
  });
});

describe("load module and PIM settings", () => {
  function withSettings(overrides: Partial<Generator> = {}) {
    const generator = sampleGenerator(overrides);
    generator.details.loadShed = {
      isConnected: true,
      parameters: [
        { definitionId: 1, displayName: "Air conditioner", value: true },
        { definitionId: 2, displayName: "Start delay", value: 5 },
        { definitionId: 3, displayName: "Module type", value: "LM-200", isReadOnly: true },
      ],
    };
    return generator;
  }

  async function openProfile(panel: RehlkoEnergyPanel) {
    document.body.append(panel);
    await settle(panel);
    clickTab(panel, "Profile");
    await settle(panel);
  }

  function submit(panel: RehlkoEnergyPanel) {
    panel.shadowRoot!.querySelector("form.dialog")!
      .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  }

  it("switches an on/off setting in place", async () => {
    const { panel, callService } = setup(sampleSnapshot([withSettings()]));
    await openProfile(panel);
    const toggle = panel.shadowRoot!.querySelector<HTMLInputElement>('.param input[type="checkbox"]')!;
    expect(toggle.getAttribute("aria-label")).toBe("Air conditioner");
    expect(toggle.checked).toBe(true);
    toggle.click();
    await settle(panel);
    expect(callService).toHaveBeenCalledWith("rehlko_energy", "set_peripheral_value",
      { device_id: "ha-device-1", definition_id: "1", value: false });
  });

  it("puts a switch back when the write fails", async () => {
    const { panel, callService } = setup(sampleSnapshot([withSettings()]));
    await openProfile(panel);
    callService.mockRejectedValue({ message: "Home generator is offline" });
    const toggle = panel.shadowRoot!.querySelector<HTMLInputElement>('.param input[type="checkbox"]')!;
    toggle.click();
    await settle(panel);
    await settle(panel);
    expect(toggle.checked).toBe(true);
    expect(panel.shadowRoot!.textContent).toContain("Home generator is offline");
  });

  it("renames a setting and writes its value from one dialog", async () => {
    const { panel, callService } = setup(sampleSnapshot([withSettings()]));
    await openProfile(panel);
    panel.shadowRoot!.querySelector<HTMLButtonElement>('[aria-label="Edit Start delay"]')!.click();
    await settle(panel);
    const name = panel.shadowRoot!.querySelector<HTMLInputElement>("#edit-name")!;
    const value = panel.shadowRoot!.querySelector<HTMLInputElement>("#edit-value")!;
    expect([name.value, value.value, value.type]).toEqual(["Start delay", "5", "number"]);
    name.value = "  Restart delay ";
    value.value = "8";
    submit(panel);
    await settle(panel);
    await settle(panel);
    expect(callService.mock.calls).toEqual([
      ["rehlko_energy", "rename_peripheral", { device_id: "ha-device-1", definition_id: "2", name: "Restart delay" }],
      ["rehlko_energy", "set_peripheral_value", { device_id: "ha-device-1", definition_id: "2", value: 8 }],
    ]);
    expect(panel.shadowRoot!.querySelector("form.dialog")).toBeNull();
  });

  it("sends nothing when nothing was changed, and refuses a blank name or value", async () => {
    const { panel, callService } = setup(sampleSnapshot([withSettings()]));
    await openProfile(panel);
    const edit = () => panel.shadowRoot!.querySelector<HTMLButtonElement>('[aria-label="Edit Start delay"]')!;
    edit().click();
    await settle(panel);
    submit(panel);
    await settle(panel);
    expect(callService).not.toHaveBeenCalled();

    edit().click();
    await settle(panel);
    panel.shadowRoot!.querySelector<HTMLInputElement>("#edit-name")!.value = "   ";
    submit(panel);
    await settle(panel);
    expect(panel.shadowRoot!.textContent).toContain("Enter a name.");
    panel.shadowRoot!.querySelector<HTMLInputElement>("#edit-name")!.value = "Start delay";
    panel.shadowRoot!.querySelector<HTMLInputElement>("#edit-value")!.value = "";
    submit(panel);
    await settle(panel);
    expect(panel.shadowRoot!.textContent).toContain("Enter a valid value.");
    expect(panel.shadowRoot!.querySelector("form.dialog")).not.toBeNull();
    expect(callService).not.toHaveBeenCalled();
  });

  it("offers a name-only dialog for a switch, and Escape closes it", async () => {
    const { panel } = setup(sampleSnapshot([withSettings()]));
    await openProfile(panel);
    panel.shadowRoot!.querySelector<HTMLButtonElement>('[aria-label="Edit Air conditioner"]')!.click();
    await settle(panel);
    expect(panel.shadowRoot!.querySelector("#edit-name")).not.toBeNull();
    expect(panel.shadowRoot!.querySelector("#edit-value")).toBeNull();
    panel.shadowRoot!.querySelector(".scrim")!
      .dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await settle(panel);
    expect(panel.shadowRoot!.querySelector("form.dialog")).toBeNull();
  });

  it("shows read-only settings, and every setting of an unreachable generator, as plain values", async () => {
    const { panel, send } = setup(sampleSnapshot([withSettings()]));
    await openProfile(panel);
    const editors = () => panel.shadowRoot!.querySelectorAll('.param button, .param input').length;
    expect(panel.shadowRoot!.querySelector('[aria-label="Edit Module type"]')).toBeNull();
    expect(panel.shadowRoot!.textContent).toContain("LM-200");
    expect(editors()).toBe(3); // a switch and its editor, and the delay's editor

    const offline = withSettings();
    offline.derived = { ...offline.derived, is_connected: false };
    send(sampleSnapshot([offline]));
    await settle(panel);
    expect(editors()).toBe(0);
    expect(panel.shadowRoot!.textContent).toContain("Air conditioner");
  });
});
