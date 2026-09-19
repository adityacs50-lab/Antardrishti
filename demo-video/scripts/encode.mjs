/**
 * Turns Remotion's high-bitrate master into the file that actually gets shared.
 *
 *   npm run encode
 *
 * Three things here are deliberate and easy to lose by hand-rolling the ffmpeg
 * call:
 *
 *  - Remotion renders from JPEG frames, so its master is tagged yuvj420p
 *    (full-range). Handing that to a player that assumes limited range crushes
 *    the blacks — and this video is almost entirely dark UI. The scale filter
 *    converts full to limited properly instead of just relabelling it.
 *  - The BT.709 tags are written explicitly so players do not have to guess.
 *  - +faststart moves the index to the front of the file, so the video starts
 *    playing over HTTP instead of downloading in full first.
 */
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const root = path.join(import.meta.dirname, "..");
const IN = path.join(root, "out", "prahari-demo.mp4");
const OUT = path.join(root, "out", "prahari-sih26165-demo.mp4");

// Use the ffmpeg that ships inside Remotion's compositor — no system install.
const ffmpeg = ["gnu", "musl"]
  .map((libc) => path.join(root, "node_modules", `@remotion/compositor-linux-x64-${libc}`, "ffmpeg"))
  .find((p) => fs.existsSync(p));

if (!ffmpeg) {
  console.error("No bundled ffmpeg found. Run `npm install` first.");
  process.exit(1);
}
if (!fs.existsSync(IN)) {
  console.error(`Missing ${IN} — run \`npm run render\` first.`);
  process.exit(1);
}

execFileSync(
  ffmpeg,
  [
    "-y", "-v", "error",
    "-i", IN,
    "-vf", "scale=in_range=full:out_range=limited,format=yuv420p",
    "-c:v", "libx264",
    "-preset", "slow",
    "-crf", "21",
    "-profile:v", "high",
    "-level", "4.1",
    "-colorspace", "bt709",
    "-color_primaries", "bt709",
    "-color_trc", "bt709",
    "-color_range", "tv",
    "-x264-params", "keyint=60:min-keyint=30",
    "-movflags", "+faststart",
    "-an",
    OUT,
  ],
  { stdio: "inherit" },
);

const mb = (fs.statSync(OUT).size / 1e6).toFixed(1);
console.log(`\n${OUT}  (${mb} MB)`);
console.log(`Copy to the repo's demo folder with:\n  cp "${OUT}" ../demo/prahari-sih26165-demo.mp4`);
