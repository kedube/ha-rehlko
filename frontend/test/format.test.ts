import { describe, it, expect } from "vitest";
import {
  DEFAULT_FORMAT, addressText, fmtDateTime, fmtDays, fmtDuration, fmtNumber, formatFrom,
  fromInputValue, humanize, num, parseTs, power, pressure, slugify, temperature, toInputValue,
  type Format,
} from "../src/format";
import { generatorState } from "../src/generator-visual";
import type { HomeAssistant } from "../src/types";

const hass = (overrides: Partial<HomeAssistant>): HomeAssistant => overrides as HomeAssistant;
const format = (overrides: Partial<Format>): Format => ({ ...DEFAULT_FORMAT, ...overrides });

describe("humanize", () => {
  it("splits PascalCase and keeps acronyms", () => {
    expect(humanize("LowOilPressureWarning")).toBe("Low oil pressure warning");
    expect(humanize("AtsExerciseActive")).toBe("ATS exercise active");
    expect(humanize("EcmPowered")).toBe("ECM powered");
    expect(humanize("EcoExercise")).toBe("Eco exercise");
  });
  it("handles empty and spaced input", () => {
    expect(humanize(null)).toBe("");
    expect(humanize("")).toBe("");
    expect(humanize("already spaced")).toBe("Already spaced");
  });
});

describe("numbers", () => {
  it("parses numbers and rejects junk", () => {
    expect(num("12.5")).toBe(12.5);
    expect(num(true)).toBeNull();
    expect(num("")).toBeNull();
    expect(num(null)).toBeNull();
  });
  it("rounds to fixed digits", () => {
    expect(fmtNumber("12.345", DEFAULT_FORMAT, 1)).toBe("12.3");
    expect(fmtNumber(240)).toBe("240");
    expect(fmtNumber(undefined)).toBeNull();
  });
  it("uses the viewer's separators", () => {
    expect(fmtNumber(1234.5, format({ numberLocale: "de" }), 1)).toBe("1.234,5");
    expect(fmtNumber(1234.5, format({ numberLocale: "en-US" }), 1)).toBe("1,234.5");
    expect(fmtNumber(1234.5, format({ numberLocale: "en-US", grouping: false }), 1)).toBe("1234.5");
  });
});

describe("units", () => {
  it("keeps the API's units for US customary and converts for metric", () => {
    expect(temperature(212)).toEqual({ text: "212", unit: "°F" });
    expect(temperature(212, format({ metric: true }))).toEqual({ text: "100", unit: "°C" });
    expect(pressure(50)).toEqual({ text: "50", unit: "psi" });
    expect(pressure(50, format({ metric: true }))).toEqual({ text: "345", unit: "kPa" });
    expect(temperature(null)).toBeNull();
  });
  it("scales power", () => {
    expect(power(850)).toEqual({ text: "850", unit: "W" });
    expect(power(5400)).toEqual({ text: "5.4", unit: "kW" });
    expect(power("")).toBeNull();
  });
  it("names durations in the viewer's language", () => {
    expect(fmtDuration(20, format({ language: "en" }))).toBe("20 min");
    expect(fmtDuration(90, format({ language: "en" }))).toBe("1 hr 30 min");
    expect(fmtDuration(60, format({ language: "es" }))).toBe("1 h");
    expect(fmtDuration(null)).toBe("—");
    expect(fmtDays(365, format({ language: "en" }))).toBe("365 days");
    expect(fmtDays(365, format({ language: "de" }))).toBe("365 Tage");
  });
});

describe("formatFrom", () => {
  it("reads language, number, clock, zone and unit preferences from Home Assistant", () => {
    const result = formatFrom(hass({
      language: "en",
      locale: { language: "fr", number_format: "decimal_comma", time_format: "24", time_zone: "server" },
      config: { time_zone: "America/Chicago", unit_system: { temperature: "°C", pressure: "Pa" } },
    }));
    expect(result).toEqual({
      language: "fr", numberLocale: "de", grouping: true, hour12: false,
      timeZone: "America/Chicago", serverTimeZone: "America/Chicago", metric: true,
    });
  });
  it("falls back to the browser for anything Home Assistant does not say", () => {
    expect(formatFrom(undefined)).toEqual({
      language: undefined, numberLocale: undefined, grouping: true, hour12: undefined,
      timeZone: undefined, serverTimeZone: undefined, metric: false,
    });
    expect(formatFrom(hass({ language: "not a tag", config: { time_zone: "Nowhere/Nope" } })).language).toBeUndefined();
    expect(formatFrom(hass({ config: { time_zone: "Nowhere/Nope" } })).serverTimeZone).toBeUndefined();
    expect(formatFrom(hass({ locale: { language: "pt-BR", number_format: "none" } })).grouping).toBe(false);
  });
});

describe("parseTs", () => {
  it("accepts Z, offsets and .NET fractions, rejects MinValue", () => {
    expect(parseTs("2026-11-12T20:00:00Z")?.getUTCHours()).toBe(20);
    expect(parseTs("2026-11-12T20:00:00.7399592+00:00")?.getUTCMinutes()).toBe(0);
    expect(parseTs("0001-01-01T00:00:00")).toBeNull();
    expect(parseTs("")).toBeNull();
    expect(parseTs(null)).toBeNull();
  });
  it("reads offset-less times in the server's zone, on either side of daylight saving", () => {
    expect(parseTs("2026-07-01T14:00:00", "America/New_York")?.toISOString()).toBe("2026-07-01T18:00:00.000Z");
    expect(parseTs("2026-12-01T14:00:00", "America/New_York")?.toISOString()).toBe("2026-12-01T19:00:00.000Z");
    expect(parseTs("2026-03-08T03:30:00", "America/New_York")?.toISOString()).toBe("2026-03-08T07:30:00.000Z");
    expect(parseTs("2026-07-01T14:00:00Z", "America/New_York")?.toISOString()).toBe("2026-07-01T14:00:00.000Z");
  });
});

describe("dates", () => {
  const prefs = format({ language: "en-US", serverTimeZone: "America/New_York", timeZone: "America/New_York" });
  it("shows times in the chosen zone and clock", () => {
    expect(fmtDateTime("2026-11-22T14:00:00", prefs)).toBe("Nov 22, 2026, 2:00 PM");
    expect(fmtDateTime("2026-11-22T14:00:00", { ...prefs, hour12: false })).toBe("Nov 22, 2026, 14:00");
    expect(fmtDateTime("2026-11-22T19:00:00Z", { ...prefs, timeZone: "America/Los_Angeles" })).toBe("Nov 22, 2026, 11:00 AM");
    expect(fmtDateTime(undefined, prefs)).toBe("—");
  });
  it("round-trips the schedule editor's value in the viewer's zone", () => {
    const viewer = format({ serverTimeZone: "America/New_York", timeZone: "America/Los_Angeles" });
    expect(toInputValue("2026-11-22T14:00:00", viewer)).toBe("2026-11-22T11:00");
    expect(fromInputValue("2026-11-22T11:00", viewer)?.toISOString()).toBe("2026-11-22T19:00:00.000Z");
    expect(toInputValue("nonsense", viewer)).toBe("");
    expect(fromInputValue("nonsense", viewer)).toBeNull();
  });
  it("uses the browser's zone when the viewer has not chosen the server's", () => {
    const local = new Date(2026, 10, 22, 9, 30);
    expect(toInputValue(local.toISOString())).toBe("2026-11-22T09:30");
    expect(fromInputValue("2026-11-22T09:30")?.getTime()).toBe(local.getTime());
  });
});

describe("addressText", () => {
  it("joins present parts", () => {
    expect(addressText({ address1: "1 Main St", city: "Town", postalCode: "12345" })).toBe("1 Main St, Town, 12345");
    expect(addressText(null)).toBe("");
  });
});

describe("slugify", () => {
  it("snake-cases wire values", () => {
    expect(slugify("EveryOtherWeek")).toBe("every_other_week");
    expect(slugify("ReadyToRun")).toBe("ready_to_run");
  });
});

describe("generatorState", () => {
  const base = { is_connected: true, is_running: false, is_exercising: false, e_stop_engaged: false, hasCriticalFault: false };
  it("prioritises offline, estop, fault, then activity", () => {
    expect(generatorState({ ...base, is_connected: false })).toBe("offline");
    expect(generatorState({ ...base, e_stop_engaged: true })).toBe("estop");
    expect(generatorState({ ...base, hasCriticalFault: true })).toBe("fault");
    expect(generatorState({ ...base, is_exercising: true })).toBe("exercising");
    expect(generatorState({ ...base, is_running: true })).toBe("running");
    expect(generatorState(base)).toBe("standby");
  });
  it("offline wins over a running flag", () => {
    expect(generatorState({ ...base, is_connected: false, is_running: true })).toBe("offline");
  });
});
