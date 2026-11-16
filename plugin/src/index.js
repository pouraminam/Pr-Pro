/**
 * Premiere AI Editor - Main Entry Point for Adobe Premiere Pro UXP Panel.
 */

import { PanelController } from "./ui/panel.js";
import { Logger } from "./utilities/logger.js";

document.addEventListener("DOMContentLoaded", async () => {
  Logger.info("Premiere AI Editor panel initializing...");

  const root = document.getElementById("root") || document.body;
  const controller = new PanelController(root);

  try {
    await controller.init();
    Logger.info("Premiere AI Editor panel ready.");
  } catch (err) {
    Logger.error("Failed to initialize Premiere AI Editor panel", err);
  }
});
