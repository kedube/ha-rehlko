import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import en from "../src/locales/en.json";
import { availableLanguages, localizer, resolveLanguage } from "../src/localize";

const LOCALES = import.meta.glob<Record<string, string>>("../src/locales/*.json", { eager: true, import: "default" });
const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort();
const SOURCE_DIR = join(__dirname, "../src");
const SOURCE = readdirSync(SOURCE_DIR).filter((name) => name.endsWith(".ts"))
  .map((name) => readFileSync(join(SOURCE_DIR, name), "utf8")).join("\n");

describe("locale files", () => {
  it.each(Object.entries(LOCALES))("%s only has messages English has, with the same placeholders", (_path, locale) => {
    for (const [key, text] of Object.entries(locale)) {
      expect(en, `unknown message ${key}`).toHaveProperty([key]);
      expect(text.trim(), `${key} is empty or padded`).toBe(text);
      expect(text, `${key} is empty`).not.toBe("");
      expect(placeholders(text), `${key} placeholders`).toEqual(placeholders(en[key as keyof typeof en]));
    }
  });

  it("ships every language the integration is translated into", () => {
    const integration = readdirSync(join(__dirname, "../../custom_components/rehlko_energy/translations"))
      .map((name) => name.replace(/\.json$/, "").toLowerCase()).sort();
    expect(availableLanguages()).toEqual(integration);
  });

  it("uses every English message, so none is translated for nothing", () => {
    const unused = Object.keys(en).filter((key) => {
      const [group] = key.split(".");
      // `tab.${tab}` is assembled from the tab's id.
      return !SOURCE.includes(`"${key}"`) && !(group === "tab" && SOURCE.includes("`tab.${"));
    });
    expect(unused).toEqual([]);
  });
});

describe("localizer", () => {
  it("resolves regional and legacy tags to the file that covers them", () => {
    expect(resolveLanguage("en")).toBe("en");
    expect(resolveLanguage("en-GB")).toBe("en");
    expect(resolveLanguage("es-419")).toBe("es");
    expect(resolveLanguage("pt")).toBe("pt-br");
    expect(resolveLanguage("pt-BR")).toBe("pt-br");
    expect(resolveLanguage("zh-Hans")).toBe("zh-hans");
    expect(resolveLanguage("zh-CN")).toBe("zh-hans");
    expect(resolveLanguage("zh-Hant")).toBe("en");
    expect(resolveLanguage("tlh")).toBe("en");
    expect(resolveLanguage(undefined)).toBe("en");
  });

  it("fills placeholders and leaves unknown ones visible", () => {
    const t = localizer("en");
    expect(t("activity.fmi", { value: 5 })).toBe("FMI 5");
    expect(t("controls.controller_clock", {})).toBe("Controller clock: {time}");
    expect(t("tab.overview")).toBe("Overview");
  });
});
