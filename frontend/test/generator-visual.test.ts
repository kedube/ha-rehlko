import { describe, expect, it } from "vitest";
import { generatorImage } from "../src/generator-visual";
import { sampleGenerator } from "./fixtures";

function product(model: string, modelDisplayName?: string) {
  return generatorImage(sampleGenerator({ device: { model, modelDisplayName } }));
}

describe("manufacturer product imagery", () => {
  it.each(["26RCA", "Model26RCA0", "Model26RCAA", "26RCA-QS1", "26RCAL", "20RCA", "14RCA"])(
    "uses the verified RCA enclosure for %s", (model) => {
      const image = product(model);
      expect(image.family).toBe("rca");
      expect(image.representative).toBe(false);
      expect(image.width / image.height).toBeCloseTo(1000 / 626);
    },
  );

  it.each([
    ["12RESV", "resv"], ["30RCLA", "rcla"], ["48RCLC", "rclc"],
  ])("selects the actual %s image", (model, family) => {
    const image = product(model);
    expect(image.family).toBe(family);
    expect(image.representative).toBe(false);
  });

  it.each([
    ["Model24RCL", "rcla"], ["Model38RCLB", "rcla"], ["Model48RCLB", "rclc"],
    ["Model60RCLH", "rclc"], ["Model130RCLGB", "rclc"], ["Model10RESV", "resv"],
    ["Model6VSG48V", "resv"], ["Other", "rca"],
  ])("labels the image for %s as representative", (model, family) => {
    const image = product(model);
    expect(image.family).toBe(family);
    expect(image.representative).toBe(true);
    expect(image.caption).toBe("");
  });

  it("uses the API model when the display name is just wattage", () => {
    expect(product("Model26RCAA", "26 kW").caption).toBe("KOHLER 26RCA");
  });

  it("does not claim a bare wattage identifies the enclosure", () => {
    expect(product("Model20KW").representative).toBe(true);
  });

  it("uses a liquid-cooled representative when only cooling type is known", () => {
    const gen = sampleGenerator({ device: {} });
    gen.details.coolingType = "Liquid";
    expect(generatorImage(gen).family).toBe("rcla");
    expect(generatorImage(gen).representative).toBe(true);
  });

  it("can use generator details when the device summary has no model", () => {
    const gen = sampleGenerator({ device: {} });
    gen.details.generators = [{ model: "Model26RCAA" }];
    expect(generatorImage(gen).caption).toBe("KOHLER 26RCA");
  });

  it("keeps the same product image across running, fault and offline states", () => {
    const gen = sampleGenerator({ device: { model: "Model26RCAA" } });
    const before = generatorImage(gen);
    gen.derived.is_running = true;
    gen.alerts = [{ isCriticalFault: true }];
    gen.derived.is_connected = false;
    expect(generatorImage(gen)).toEqual(before);
  });
});
