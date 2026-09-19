import fs from "node:fs";
import path from "node:path";
import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);

/**
 * Remotion's renderer drives Chromium through the *old* headless mode, which
 * Chrome 1194+ removed from the main binary ("Old Headless mode has been
 * removed... use chrome-headless-shell"). The standalone headless shell still
 * implements it, and ships alongside Chromium in the Playwright browser bundle,
 * so prefer it when one is present.
 *
 * Override with REMOTION_BROWSER_EXECUTABLE, or delete this block on a machine
 * whose default Chromium still supports old headless.
 */
const PW = process.env.PLAYWRIGHT_BROWSERS_PATH || "/opt/pw-browsers";

const headlessShell = (): string | null => {
  const explicit = process.env.REMOTION_BROWSER_EXECUTABLE;
  if (explicit) return fs.existsSync(explicit) ? explicit : null;
  if (!fs.existsSync(PW)) return null;
  const dirs = fs
    .readdirSync(PW)
    .filter((d) => d.startsWith("chromium_headless_shell-"))
    .sort()
    .reverse(); // highest build number first
  for (const d of dirs) {
    const bin = path.join(PW, d, "chrome-linux", "headless_shell");
    if (fs.existsSync(bin)) return bin;
  }
  return null;
};

const shell = headlessShell();
if (shell) {
  Config.setBrowserExecutable(shell);
}
