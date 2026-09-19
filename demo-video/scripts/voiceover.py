#!/usr/bin/env python3
"""
Builds the demo video's narration track and muxes it onto the rendered video.

    python3 scripts/voiceover.py

Reads narration.json, synthesises one clip per cue with Piper (a neural TTS that
runs offline on CPU), lays each clip at its cue's timestamp, normalises the
result and writes out/prahari-sih26165-demo.mp4 with the voice attached.

The cue timings belong to the scene boundaries in src/PrahariDemo.tsx. This
script re-checks every cue against the scene window recorded alongside it and
refuses to build a track where a line would run past its scene — otherwise a
retimed scene silently produces a video whose voice talks over the next shot.

The voice model is ~120 MB and is not tracked in the repo. Fetch it once:

    mkdir -p voices && cd voices
    curl -L -O https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-en-us-ryan-high.tar.gz
    tar xzf voice-en-us-ryan-high.tar.gz

and install the synthesiser with `pip install piper-tts`. Both are build-time
only: nothing here ships in the app, and prahari itself still makes no network
calls at runtime.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "narration.json"
VIDEO_IN = ROOT / "out" / "prahari-demo.mp4"
VIDEO_OUT = ROOT / "out" / "prahari-sih26165-demo.mp4"

# Headroom between the end of a line and the end of its scene. Landing a word
# on the cut sounds like a mistake even when it technically fits.
TAIL_GAP = 0.15


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def find_ffmpeg() -> str:
    """Prefer the ffmpeg bundled inside Remotion's compositor; fall back to PATH."""
    for libc in ("gnu", "musl"):
        p = ROOT / "node_modules" / f"@remotion/compositor-linux-x64-{libc}" / "ffmpeg"
        if p.exists():
            return str(p)
    found = shutil.which("ffmpeg")
    if found:
        return found
    die("no ffmpeg found — run `npm install` in demo-video/")
    raise AssertionError  # unreachable, keeps type checkers happy


def find_voice(name: str) -> Path:
    for candidate in (ROOT / "voices" / f"{name}.onnx", Path(f"{name}.onnx")):
        if candidate.exists():
            return candidate
    die(
        f"voice model {name}.onnx not found in {ROOT / 'voices'} — "
        "see the fetch command in this script's docstring"
    )
    raise AssertionError


def duration(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def synthesise(text: str, model: Path, out: Path, speaker: int | None) -> float:
    cmd = [sys.executable, "-m", "piper", "--model", str(model), "--output_file", str(out)]
    if speaker is not None:  # multi-speaker models (LibriTTS) need one picked
        cmd += ["--speaker", str(speaker)]
    proc = subprocess.run(cmd, input=text.encode(), capture_output=True)
    if proc.returncode != 0 or not out.exists():
        die(f"piper failed: {proc.stderr.decode()[:400]}")
    return duration(out)


def main() -> None:
    if not VIDEO_IN.exists():
        die(f"missing {VIDEO_IN} — run `npm run render` first")

    spec = json.loads(SPEC.read_text())
    cues = spec["cues"]
    model = find_voice(spec["voice"])
    speaker = spec.get("speaker")
    ffmpeg = find_ffmpeg()

    work = Path(tempfile.mkdtemp(prefix="prahari-vo-"))
    try:
        clips: list[tuple[Path, float]] = []
        problems: list[str] = []

        print(f"synthesising {len(cues)} cues with {model.name}")
        for cue in cues:
            clip = work / f"{cue['scene']}.wav"
            dur = synthesise(cue["text"], model, clip, speaker)
            ends = cue["at"] + dur
            limit = cue["scene_end"] - TAIL_GAP

            if cue["at"] < cue["scene_start"]:
                problems.append(
                    f"  {cue['scene']}: starts at {cue['at']:.2f}s, "
                    f"before its scene opens at {cue['scene_start']:.2f}s"
                )
            if ends > limit:
                problems.append(
                    f"  {cue['scene']}: runs to {ends:.2f}s, past its scene "
                    f"({cue['scene_end']:.2f}s) — shorten the line or retime it"
                )
            print(f"  {cue['scene']:<10} {cue['at']:>6.2f}s  +{dur:>5.2f}s -> {ends:>6.2f}s")
            clips.append((clip, cue["at"]))

        if problems:
            die("narration does not fit the edit:\n" + "\n".join(problems))

        # Lay each clip at its offset, sum them (they never overlap, so mixing
        # must not rescale), then normalise for consistent playback level.
        inputs: list[str] = []
        for clip, _ in clips:
            inputs += ["-i", str(clip)]

        chain = "".join(
            f"[{i + 1}:a]aresample=48000,adelay={int(at * 1000)}:all=1[v{i}];"
            for i, (_, at) in enumerate(clips)
        )
        mix = "".join(f"[v{i}]" for i in range(len(clips)))
        chain += (
            f"{mix}amix=inputs={len(clips)}:normalize=0,"
            "loudnorm=I=-16:TP=-1.5:LRA=11,aformat=sample_fmts=fltp:channel_layouts=stereo[a]"
        )

        print("\nmixing and muxing")
        subprocess.run(
            [
                ffmpeg, "-y", "-v", "error",
                "-i", str(VIDEO_IN), *inputs,
                "-filter_complex", chain,
                "-map", "0:v:0", "-map", "[a]",
                # Re-encode the picture for delivery: limited-range BT.709 and a
                # front-loaded index, matching scripts/encode.mjs.
                "-vf", "scale=in_range=full:out_range=limited,format=yuv420p",
                "-c:v", "libx264", "-preset", "slow", "-crf", "21",
                "-profile:v", "high", "-level", "4.1",
                "-colorspace", "bt709", "-color_primaries", "bt709",
                "-color_trc", "bt709", "-color_range", "tv",
                "-x264-params", "keyint=60:min-keyint=30",
                "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
                "-movflags", "+faststart",
                str(VIDEO_OUT),
            ],
            check=True,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)

    mb = VIDEO_OUT.stat().st_size / 1e6
    print(f"\n{VIDEO_OUT}  ({mb:.1f} MB, with narration)")
    print(f"Copy to the repo's demo folder with:\n  cp {VIDEO_OUT} ../demo/prahari-sih26165-demo.mp4")


if __name__ == "__main__":
    main()
