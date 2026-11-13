// The panel's own text. Each language is one file in ./locales, keyed by message id, with
// en.json as the source; a language file may be incomplete and falls back to English key by
// key. Enum values (engine states, exercise modes, …) are not repeated here: the panel reads
// those from the integration's entity translations through `hass.localize`.

import en from "./locales/en.json";

export type MessageKey = keyof typeof en;
export type Localize = (key: MessageKey, values?: Record<string, string | number>) => string;

type Dictionary = Partial<Record<MessageKey, string>>;

// Every file in ./locales is bundled, so adding a language is adding its file.
const FILES = import.meta.glob<Dictionary>("./locales/*.json", { eager: true, import: "default" });
const LOCALES: Record<string, Dictionary> = {};
for (const [path, dictionary] of Object.entries(FILES)) {
  LOCALES[path.replace(/^.*\/|\.json$/g, "").toLowerCase()] = dictionary;
}

// Home Assistant tags that should use a locale filed under another tag. Only exact tags are
// listed: `zh-Hant` must not fall through to the Simplified Chinese file.
const ALIASES: Record<string, string> = {
  pt: "pt-br", "pt-pt": "pt-br", zh: "zh-hans", "zh-cn": "zh-hans", "zh-sg": "zh-hans",
};

/** The locale file used for a Home Assistant language tag such as `es-419` (`en` if none). */
export function resolveLanguage(language?: string): string {
  const tag = (language ?? "en").toLowerCase();
  for (const candidate of [tag, ALIASES[tag], tag.split("-")[0]]) {
    if (candidate && LOCALES[candidate]) return candidate;
  }
  return "en";
}

export function availableLanguages(): string[] {
  return Object.keys(LOCALES).sort();
}

const cache = new Map<string, Localize>();

export function localizer(language?: string): Localize {
  const resolved = resolveLanguage(language);
  let localize = cache.get(resolved);
  if (!localize) {
    const dictionary = LOCALES[resolved] ?? {};
    localize = (key, values) => {
      const template = dictionary[key] || en[key] || key;
      return values
        ? template.replace(/\{(\w+)\}/g, (match, name: string) => (name in values ? String(values[name]) : match))
        : template;
    };
    cache.set(resolved, localize);
  }
  return localize;
}
