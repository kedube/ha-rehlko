import rcaImage from "./assets/generator-rca.webp";
import resvImage from "./assets/generator-resv.webp";
import rclaImage from "./assets/generator-rcla.webp";
import rclcImage from "./assets/generator-rclc.webp";
import type { Generator } from "./types";

export type VisualState = "offline" | "standby" | "running" | "exercising" | "fault" | "estop";

export function generatorState(d: {
  is_connected: boolean;
  is_running: boolean;
  is_exercising: boolean;
  e_stop_engaged: boolean;
  hasCriticalFault: boolean;
}): VisualState {
  if (!d.is_connected) return "offline";
  if (d.e_stop_engaged) return "estop";
  if (d.hasCriticalFault) return "fault";
  if (d.is_exercising) return "exercising";
  if (d.is_running) return "running";
  return "standby";
}

type ImageFamily = "rca" | "resv" | "rcla" | "rclc";

interface ProductImage {
  src: string;
  width: number;
  height: number;
  /** The pictured product's name, which is the same in every language. */
  description: string;
}

export interface GeneratorImage extends ProductImage {
  family: ImageFamily;
  /** The matched model's name; empty for a representative image, which the panel labels. */
  caption: string;
  representative: boolean;
}

// Authentic manufacturer images, bundled locally with the panel. These never change
// enclosure colour, geometry or hardware according to operating state. See assets/README.md.
const IMAGES: Record<ImageFamily, ProductImage> = {
  rca: { src: rcaImage, width: 1000, height: 626, description: "KOHLER RCA" },
  resv: { src: resvImage, width: 1000, height: 667, description: "KOHLER 12RESV" },
  rcla: { src: rclaImage, width: 1000, height: 667, description: "KOHLER 30RCLA" },
  rclc: { src: rclcImage, width: 1000, height: 667, description: "KOHLER 48RCLC" },
};

function normalizedModel(value: unknown): string {
  return typeof value === "string" ? value.toUpperCase().replace(/[^A-Z0-9]/g, "").replace(/^MODEL/, "") : "";
}

export function generatorImage(gen: Generator): GeneratorImage {
  const models = [gen.device.modelDisplayName, gen.device.model,
    ...(gen.details.generators ?? []).flatMap((g) => [g.modelDisplayName, g.model])]
    .map(normalizedModel).filter(Boolean);
  let family: ImageFamily | undefined;
  let caption = "";
  let representative = false;

  // Match actual model identifiers, including the API's Model26RCA0/Model26RCAA
  // enum values and dealer SKU suffixes. Do not interpret a bare wattage as a model.
  for (const model of models) {
    const rca = model.match(/^(14|20|26)RCAL?(?:A|0)?(?:QS\d.*)?$/);
    if (rca) {
      family = "rca";
      caption = `KOHLER ${rca[1]}RCA`;
    } else if (/^12RESVL?(?:QS\d.*)?$/.test(model)) {
      family = "resv";
      caption = "KOHLER 12RESV";
    } else if (/^30RCLA(?:QS\d.*)?$/.test(model)) {
      family = "rcla";
      caption = "KOHLER 30RCLA";
    } else if (/^48RCLC(?:QS\d.*)?$/.test(model)) {
      family = "rclc";
      caption = "KOHLER 48RCLC";
    }
    if (family) break;
  }

  if (!family) {
    representative = true;
    // Older and newer RCL enclosures differ. Use the closest available size family
    // and explicitly label its image, preserving every user's real model elsewhere.
    if (models.some((model) => /^(?:4[058]|60|130)RCL/.test(model))) family = "rclc";
    else if (models.some((model) => /^\d+RCL/.test(model))) family = "rcla";
    else if (models.some((model) => /^(?:8|10|12)RESV|^6VSG/.test(model))) family = "resv";
    else if (normalizedModel(gen.details.coolingType) === "LIQUID") family = "rcla";
    else family = "rca";
  }

  return { ...IMAGES[family], family, caption, representative };
}
