// Load the file that ships in the integration, independently of the TypeScript source.
import "../../custom_components/rehlko_energy/www/rehlko-energy-panel.js";
import { afterEach, expect, it } from "vitest";
import type { HomeAssistant } from "../src/types";
import { sampleSnapshot } from "./fixtures";

afterEach(() => document.body.replaceChildren());

it("the production bundle defines and renders a working custom panel", async () => {
  const panel = document.createElement("rehlko-energy-panel") as HTMLElement & {
    hass: HomeAssistant; updateComplete: Promise<boolean>;
  };
  let unsubscribed = false;
  panel.hass = {
    states: {},
    connection: {
      async subscribeMessage<T>(callback: (value: T) => void) {
        callback(sampleSnapshot() as T);
        return () => { unsubscribed = true; };
      },
    },
  } as unknown as HomeAssistant;
  document.body.append(panel);
  await panel.updateComplete;
  await Promise.resolve();
  expect(panel.shadowRoot!.querySelector("h1")!.textContent).toBe("Home generator");
  expect(panel.shadowRoot!.querySelectorAll('[role="tab"]')).toHaveLength(6);
  const image = panel.shadowRoot!.querySelector<HTMLImageElement>(".generator-photo")!;
  expect(image.src).toMatch(/^data:image\/webp;base64,/);
  expect(image.width).toBe(1000);
  expect(image.height).toBe(626);
  panel.remove();
  expect(unsubscribed).toBe(true);
});
