import { type Locale } from "./locales";
import { en, type MessageKey } from "./messages/en";
import { mr } from "./messages/mr";

export type { MessageKey };
export type Messages = Record<MessageKey, string>;
export type Params = Record<string, string | number>;
export type Translator = (key: MessageKey, params?: Params) => string;

export const MESSAGES: Record<Locale, Messages> = { en, mr };

const PLACEHOLDER = /\{([a-zA-Z][a-zA-Z0-9_]*)\}/g;

/** Names of the {placeholders} in a template, in order. */
export function placeholdersOf(template: string): string[] {
  return [...template.matchAll(PLACEHOLDER)].map((m) => m[1]);
}

/**
 * Fill {name} placeholders. A missing parameter is a bug: it throws in development and tests so it is caught, and
 * renders empty in production so a page never breaks over it.
 */
export function interpolate(template: string, params?: Params): string {
  return template.replace(PLACEHOLDER, (_whole, name: string) => {
    const value = params?.[name];
    if (value === undefined) {
      if (process.env.NODE_ENV !== "production") throw new Error(`Missing i18n parameter {${name}} for "${template}"`);
      return "";
    }
    return String(value);
  });
}

export function createTranslator(locale: Locale, messages: Messages = MESSAGES[locale]): Translator {
  void locale;
  return (key, params) => interpolate(messages[key], params);
}
