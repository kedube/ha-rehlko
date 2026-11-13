// Formatting helpers shared across the panel. Pure functions, unit-tested.

import type { HomeAssistant } from "./types";

const ACRONYMS: Record<string, string> = {
  ats: "ATS", ecm: "ECM", ecu: "ECU", pim: "PIM", rpm: "RPM", gfci: "GFCI", ism: "ISM",
  ac: "AC", dc: "DC", kw: "kW", lp: "LP", ok: "OK", co: "CO", ip: "IP", id: "ID",
  l1: "L1", l2: "L2", l3: "L3", usb: "USB", mil: "MIL", rsa: "RSA",
};

export function humanize(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  if (text === "") return "";
  if (text.includes(" ")) return text.charAt(0).toUpperCase() + text.slice(1);
  const parts = text.match(/[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+[A-Za-z]?/g) ?? [text];
  return parts
    .map((part, i) => {
      const low = part.toLowerCase();
      if (ACRONYMS[low]) return ACRONYMS[low];
      if (i === 0) return part.charAt(0).toUpperCase() + part.slice(1).toLowerCase();
      return low;
    })
    .join(" ");
}

export function slugify(value: unknown): string {
  return String(value)
    .replace(/(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])/g, "_")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function num(value: unknown): number | null {
  if (value === null || value === undefined || value === "" || typeof value === "boolean") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

export function addressText(address?: {
  address1?: string; address2?: string; city?: string; postalCode?: string; country?: string;
} | null): string {
  if (!address) return "";
  return [address.address1, address.address2, address.city, address.postalCode, address.country]
    .filter(Boolean)
    .join(", ");
}

// ---- the viewer's preferences ----

/** How the person looking at the panel wants numbers, dates and units shown. */
export interface Format {
  /** Language for dates, relative times and unit names (undefined = the browser's). */
  language?: string;
  /** Locale that decides the decimal and grouping separators. */
  numberLocale?: string;
  grouping: boolean;
  /** 12- or 24-hour clock, when the user chose one over their language's default. */
  hour12?: boolean;
  /** Zone to show times in (undefined = the browser's). */
  timeZone?: string;
  /** Zone of the API's offset-less timestamps: the Home Assistant server's. */
  serverTimeZone?: string;
  /** Show °C and kPa, not the API's °F and psi. */
  metric: boolean;
}

export const DEFAULT_FORMAT: Format = { grouping: true, metric: false };

function supported(tag?: string): string | undefined {
  if (!tag) return undefined;
  try {
    return Intl.DateTimeFormat.supportedLocalesOf(tag)[0];
  } catch {
    return undefined;
  }
}

function validZone(zone?: string): string | undefined {
  if (!zone) return undefined;
  try {
    new Intl.DateTimeFormat("en", { timeZone: zone });
    return zone;
  } catch {
    return undefined;
  }
}

// Home Assistant's "number format" profile setting, as the locale that produces it.
const NUMBER_LOCALES: Record<string, string> = {
  comma_decimal: "en-US", decimal_comma: "de", space_comma: "fr", quote_decimal: "de-CH",
};

/** Read the viewer's language, number, time and unit preferences from Home Assistant. */
export function formatFrom(hass?: HomeAssistant): Format {
  const locale = hass?.locale;
  const language = supported(locale?.language ?? hass?.language);
  const numbers = locale?.number_format;
  const serverTimeZone = validZone(hass?.config?.time_zone);
  return {
    language,
    numberLocale: numbers === "system" ? undefined : NUMBER_LOCALES[numbers ?? ""] ?? language,
    grouping: numbers !== "none",
    hour12: locale?.time_format === "12" ? true : locale?.time_format === "24" ? false : undefined,
    timeZone: locale?.time_zone === "server" ? serverTimeZone : undefined,
    serverTimeZone,
    metric: hass?.config?.unit_system?.temperature === "°C",
  };
}

// ---- numbers and units ----

export function fmtNumber(value: unknown, format: Format = DEFAULT_FORMAT, digits = 0): string | null {
  const n = num(value);
  if (n === null) return null;
  return new Intl.NumberFormat(format.numberLocale, {
    minimumFractionDigits: digits, maximumFractionDigits: digits, useGrouping: format.grouping,
  }).format(n);
}

export interface Quantity { text: string; unit: string }

/** A temperature the API reports in °F, in the viewer's unit. */
export function temperature(fahrenheit: unknown, format: Format = DEFAULT_FORMAT): Quantity | null {
  const f = num(fahrenheit);
  if (f === null) return null;
  return format.metric
    ? { text: fmtNumber((f - 32) * 5 / 9, format)!, unit: "°C" }
    : { text: fmtNumber(f, format)!, unit: "°F" };
}

/** A pressure the API reports in psi, in the viewer's unit. */
export function pressure(psi: unknown, format: Format = DEFAULT_FORMAT): Quantity | null {
  const p = num(psi);
  if (p === null) return null;
  return format.metric
    ? { text: fmtNumber(p * 6.894757, format)!, unit: "kPa" }
    : { text: fmtNumber(p, format)!, unit: "psi" };
}

/** Watts as `850 W` or `5.4 kW`. */
export function power(watts: unknown, format: Format = DEFAULT_FORMAT): Quantity | null {
  const w = num(watts);
  if (w === null) return null;
  return Math.abs(w) >= 1000
    ? { text: fmtNumber(w / 1000, format, 1)!, unit: "kW" }
    : { text: fmtNumber(w, format)!, unit: "W" };
}

function unit(value: number, name: "minute" | "hour" | "day", format: Format, display: "short" | "long"): string {
  return new Intl.NumberFormat(format.language, {
    style: "unit", unit: name, unitDisplay: display, maximumFractionDigits: 0,
  }).format(value);
}

export function fmtDuration(minutes: unknown, format: Format = DEFAULT_FORMAT): string {
  const total = num(minutes);
  if (total === null) return "—";
  if (total < 60) return unit(total, "minute", format, "short");
  const hours = Math.floor(total / 60);
  const rest = Math.round(total % 60);
  return rest ? `${unit(hours, "hour", format, "short")} ${unit(rest, "minute", format, "short")}` : unit(hours, "hour", format, "short");
}

export function fmtDays(days: unknown, format: Format = DEFAULT_FORMAT): string {
  const total = num(days);
  return total === null ? "—" : unit(total, "day", format, "long");
}

// ---- timestamps ----

const WALL_CLOCK = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/;

/** How far `zone` is ahead of UTC at `instant`, in milliseconds. */
function zoneOffset(instant: number, zone: string): number {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: zone, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  }).formatToParts(instant);
  const part = (type: string) => Number(parts.find((p) => p.type === type)?.value);
  const wall = Date.UTC(part("year"), part("month") - 1, part("day"), part("hour"), part("minute"), part("second"));
  return wall - Math.floor(instant / 1000) * 1000;
}

/** The instant at which a clock in `zone` reads the wall-clock time held in `wallAsUtc`. */
function zonedInstant(wallAsUtc: number, zone: string): number {
  const guess = wallAsUtc - zoneOffset(wallAsUtc, zone);
  // Across a daylight-saving change the first guess can use the wrong side's offset.
  return wallAsUtc - zoneOffset(guess, zone);
}

/**
 * Parse the API's ISO-8601 timestamps: `…Z`, `…+00:00`, seven-digit .NET fractions, and
 * offset-less wall-clock times. The integration reads the last kind in the Home Assistant
 * server's time zone, so pass that zone to agree with it; without one they are read in the
 * browser's zone.
 */
export function parseTs(value: unknown, serverTimeZone?: string): Date | null {
  if (typeof value !== "string" || value === "") return null;
  if (value.startsWith("0001-01-01")) return null; // .NET DateTime.MinValue, i.e. "never"
  let text = value.trim().replace(/(\.\d{3})\d+/, "$1");
  if (/[zZ]$/.test(text)) text = text.slice(0, -1) + "Z";
  const naive = WALL_CLOCK.exec(text);
  if (naive && serverTimeZone && !/(Z|[+-]\d{2}:?\d{2})$/.test(text)) {
    const [, y, mo, d, h, mi, s] = naive;
    const wall = Date.UTC(Number(y), Number(mo) - 1, Number(d), Number(h), Number(mi), Number(s ?? 0));
    return new Date(zonedInstant(wall, serverTimeZone));
  }
  const date = new Date(text);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function fmtDateTime(value: unknown, format: Format = DEFAULT_FORMAT): string {
  const date = parseTs(value, format.serverTimeZone);
  if (!date) return "—";
  return date.toLocaleString(format.language, {
    dateStyle: "medium", timeStyle: "short", hour12: format.hour12, timeZone: format.timeZone,
  });
}

export function fmtRelative(value: unknown, format: Format = DEFAULT_FORMAT): string {
  const date = parseTs(value, format.serverTimeZone);
  if (!date) return "—";
  const diff = date.getTime() - Date.now();
  const abs = Math.abs(diff);
  const rtf = new Intl.RelativeTimeFormat(format.language, { numeric: "auto" });
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 31536e6], ["month", 2592e6], ["day", 864e5],
    ["hour", 36e5], ["minute", 6e4], ["second", 1e3],
  ];
  for (const [name, ms] of units) {
    if (abs >= ms || name === "second") return rtf.format(Math.round(diff / ms), name);
  }
  return "—";
}

const pad = (n: number) => String(n).padStart(2, "0");

/** A timestamp as the value of an `<input type="datetime-local">`, in the viewer's zone. */
export function toInputValue(value: unknown, format: Format = DEFAULT_FORMAT): string {
  const date = parseTs(value, format.serverTimeZone);
  if (!date) return "";
  const shown = format.timeZone
    ? new Date(date.getTime() + zoneOffset(date.getTime(), format.timeZone))
    : new Date(date.getTime() - date.getTimezoneOffset() * 6e4);
  return `${shown.getUTCFullYear()}-${pad(shown.getUTCMonth() + 1)}-${pad(shown.getUTCDate())}`
    + `T${pad(shown.getUTCHours())}:${pad(shown.getUTCMinutes())}`;
}

/** The instant a `datetime-local` value names in the viewer's zone (null if it is not one). */
export function fromInputValue(text: string, format: Format = DEFAULT_FORMAT): Date | null {
  const parts = WALL_CLOCK.exec(text);
  if (!parts) return null;
  const [, y, mo, d, h, mi] = parts;
  if (format.timeZone) {
    return new Date(zonedInstant(Date.UTC(Number(y), Number(mo) - 1, Number(d), Number(h), Number(mi)), format.timeZone));
  }
  const local = new Date(Number(y), Number(mo) - 1, Number(d), Number(h), Number(mi));
  return Number.isNaN(local.getTime()) ? null : local;
}
