import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, Easing } from "remotion";
import { C, FONT, MONO, H, W, FULL, type Rect } from "./theme";

/* ------------------------------------------------------------------ easing */

export const easeOut = Easing.bezier(0.16, 1, 0.3, 1);
export const easeInOut = Easing.bezier(0.65, 0, 0.35, 1);

/** interpolate with sane defaults: clamped, eased. */
export const ease = (
  frame: number,
  range: [number, number],
  out: [number, number],
  fn = easeOut,
) =>
  interpolate(frame, range, out, {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: fn,
  });

/* ------------------------------------------------------------------ camera */

/** Linear-in-time rect tween; the easing is applied to `t` by the caller. */
export const lerpRect = (a: Rect, b: Rect, t: number): Rect => ({
  x: a.x + (b.x - a.x) * t,
  y: a.y + (b.y - a.y) * t,
  w: a.w + (b.w - a.w) * t,
  h: a.h + (b.h - a.h) * t,
});

/**
 * Builds a 16:9 camera of width `w` that sits on `roi`, with the region's centre
 * parked `anchorY` of the way down the frame — ROIs default to the upper-middle
 * so the lower third stays free for the caption. The result is clamped to the
 * screenshot's bounds, which is what stops a push-in from running off the end of
 * the page and filling the frame with empty background.
 */
export const focus = (roi: Rect, w: number, anchorY = 0.42): Rect => {
  // Never zoom past the region itself: a full-width card asked to fill a
  // narrower camera would get its own edges cropped off.
  const width = Math.min(W, Math.max(w, roi.w + 130));
  const h = (width * 9) / 16;
  const cx = roi.x + roi.w / 2;
  const cy = roi.y + roi.h / 2;
  const clamp = (v: number, max: number) => Math.min(Math.max(0, v), Math.max(0, max));
  return {
    x: clamp(cx - width / 2, W - width),
    y: clamp(cy - h * anchorY, H - h),
    w: width,
    h,
  };
};

/** Maps a point in screenshot space to frame space under the current camera. */
export const project = (p: { x: number; y: number }, cam: Rect) => {
  const s = W / cam.w;
  return { x: (p.x - cam.x) * s, y: (p.y - cam.y) * s, s };
};

/**
 * A captured app screen under a moving camera. Children are rendered inside the
 * same transformed layer, so anything positioned in screenshot coordinates
 * (callout boxes, spotlights) tracks the UI exactly as the camera moves.
 */
export const Screen: React.FC<{
  src: string;
  cam: Rect;
  children?: React.ReactNode;
}> = ({ src, cam, children }) => {
  const s = W / cam.w;
  return (
    <AbsoluteFill style={{ backgroundColor: C.bgDeep, overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          width: W,
          height: H,
          transformOrigin: "0 0",
          transform: `scale(${s}) translate(${-cam.x}px, ${-cam.y}px)`,
        }}
      >
        <Img
          src={staticFile(src)}
          style={{ width: W, height: H, display: "block" }}
        />
        {children}
      </div>
    </AbsoluteFill>
  );
};

/* ---------------------------------------------------------------- spotlight */

/**
 * Dims everything outside `box` and draws an accent frame around it. Built from
 * four solid panels rather than a CSS mask: masks composite unevenly across
 * Chromium's tiled renderer and produced visible seams at 2x.
 */
export const Spotlight: React.FC<{
  box: Rect;
  progress: number;
  colour?: string;
  pad?: number;
}> = ({ box, progress, colour = C.accentSoft, pad = 10 }) => {
  if (progress <= 0.001) return null;
  const b = {
    x: box.x - pad,
    y: box.y - pad,
    w: box.w + pad * 2,
    h: box.h + pad * 2,
  };
  const dim = 0.72 * progress;
  const panel = (st: React.CSSProperties) => (
    <div style={{ position: "absolute", backgroundColor: `rgba(6,6,7,${dim})`, ...st }} />
  );
  return (
    <>
      {panel({ left: 0, top: 0, width: W, height: Math.max(0, b.y) })}
      {panel({ left: 0, top: b.y + b.h, width: W, height: Math.max(0, H - b.y - b.h) })}
      {panel({ left: 0, top: b.y, width: Math.max(0, b.x), height: b.h })}
      {panel({ left: b.x + b.w, top: b.y, width: Math.max(0, W - b.x - b.w), height: b.h })}
      <div
        style={{
          position: "absolute",
          left: b.x,
          top: b.y,
          width: b.w,
          height: b.h,
          border: `2px solid ${colour}`,
          borderRadius: 6,
          boxShadow: `0 0 0 1px rgba(0,0,0,.55), 0 0 44px ${colour}66`,
          opacity: progress,
        }}
      />
    </>
  );
};

/* ------------------------------------------------------------------ callout */

/**
 * A pill label pinned just outside a spotlighted element, in frame space so the
 * text stays at its designed size no matter how far the camera has pushed in.
 */
export const Callout: React.FC<{
  box: Rect;
  cam: Rect;
  label: string;
  sub?: string;
  side?: "top" | "bottom";
  colour?: string;
  progress: number;
}> = ({ box, cam, label, sub, side = "bottom", colour = C.accentSoft, progress }) => {
  const p = project({ x: box.x + box.w / 2, y: side === "bottom" ? box.y + box.h : box.y }, cam);
  const rise = (1 - progress) * 14;
  const gap = 26;

  // Keep the pill on screen even when the anchor sits near an edge: the label is
  // rendered in frame space, so an un-clamped anchor would push it out of shot.
  const halfWidth = Math.max(180, (label.length * 13 + 48) / 2);
  const left = Math.min(Math.max(halfWidth + 40, p.x), W - halfWidth - 40);
  const rawTop = side === "bottom" ? p.y + gap + rise : p.y - gap - rise;
  const top = Math.min(Math.max(side === "bottom" ? 40 : 120, rawTop), H - 150);

  return (
    <div
      style={{
        position: "absolute",
        left,
        top,
        transform: `translate(-50%, ${side === "bottom" ? "0" : "-100%"})`,
        opacity: progress,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          display: "inline-flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 3,
          padding: "10px 18px",
          borderRadius: 8,
          backgroundColor: "rgba(10,10,11,.94)",
          border: `1px solid ${colour}`,
          boxShadow: `0 10px 40px rgba(0,0,0,.6)`,
        }}
      >
        <span
          style={{
            fontFamily: FONT,
            fontWeight: 600,
            fontSize: 24,
            letterSpacing: "-0.01em",
            color: colour,
            whiteSpace: "nowrap",
          }}
        >
          {label}
        </span>
        {sub ? (
          <span
            style={{
              fontFamily: FONT,
              fontWeight: 400,
              fontSize: 17,
              color: C.text2,
              whiteSpace: "nowrap",
            }}
          >
            {sub}
          </span>
        ) : null}
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ caption */

/** Lower-third narration. One idea per card — it is read, not studied. */
export const Caption: React.FC<{
  kicker?: string;
  lines: string[];
  progress: number;
  accent?: string;
}> = ({ kicker, lines, progress, accent = C.accentSoft }) => (
  <>
    {/* Scrim: captions sit over live UI, and dark-on-dark text is unreadable
        without one. Tied to the caption's own opacity so it never lingers. */}
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 0,
        height: 430,
        opacity: progress,
        pointerEvents: "none",
        background:
          "linear-gradient(to top, rgba(4,4,5,.95) 0%, rgba(4,4,5,.86) 34%, rgba(4,4,5,.55) 66%, rgba(4,4,5,0) 100%)",
      }}
    />
    <div
      style={{
        position: "absolute",
        left: 96,
        bottom: 104,
        maxWidth: 1180,
        opacity: progress,
        transform: `translateY(${(1 - progress) * 18}px)`,
      }}
    >
    <div
      style={{
        position: "absolute",
        left: -24,
        top: 4,
        bottom: 4,
        width: 4,
        borderRadius: 2,
        backgroundColor: accent,
      }}
    />
    {kicker ? (
      <div
        style={{
          fontFamily: MONO,
          fontWeight: 600,
          fontSize: 19,
          letterSpacing: "0.14em",
          textTransform: "uppercase",
          color: accent,
          marginBottom: 12,
        }}
      >
        {kicker}
      </div>
    ) : null}
    {lines.map((l, i) => (
      <div
        key={i}
        style={{
          fontFamily: FONT,
          fontWeight: 500,
          fontSize: 41,
          lineHeight: 1.28,
          letterSpacing: "-0.018em",
          color: C.text1,
          textShadow: "0 3px 26px rgba(0,0,0,.92)",
        }}
      >
          {l}
        </div>
      ))}
    </div>
  </>
);

/* ------------------------------------------------------- framing & chrome */

/** Vignette + a faint scanline of grain. Keeps flat dark UI from looking flat. */
export const Vignette: React.FC = () => (
  <AbsoluteFill
    style={{
      pointerEvents: "none",
      background:
        "radial-gradient(120% 78% at 50% 44%, rgba(0,0,0,0) 46%, rgba(0,0,0,.30) 78%, rgba(0,0,0,.62) 100%)",
    }}
  />
);

/** Persistent chapter rail: where we are, and how much is left. */
export const ProgressRail: React.FC<{ progress: number; chapter: string; opacity: number }> = ({
  progress,
  chapter,
  opacity,
}) => (
  <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, opacity }}>
    {/* The rail sits over live UI; without its own scrim the chapter label
        collides with whatever happens to be at the foot of the screenshot. */}
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 0,
        height: 108,
        background: "linear-gradient(to top, rgba(4,4,5,.92) 0%, rgba(4,4,5,0) 100%)",
        pointerEvents: "none",
      }}
    />
    <div
      style={{
        position: "relative",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 44px 18px",
      }}
    >
      <span
        style={{
          fontFamily: MONO,
          fontSize: 17,
          letterSpacing: "0.13em",
          textTransform: "uppercase",
          color: C.text3,
        }}
      >
        {chapter}
      </span>
      <span
        style={{
          fontFamily: MONO,
          fontSize: 17,
          letterSpacing: "0.13em",
          color: C.text3,
        }}
      >
        prahari · SIH26165
      </span>
    </div>
    <div style={{ position: "relative", height: 3, backgroundColor: "rgba(255,255,255,.08)" }}>
      <div
        style={{
          height: 3,
          width: `${progress * 100}%`,
          backgroundColor: C.accent,
          boxShadow: `0 0 16px ${C.accent}`,
        }}
      />
    </div>
  </div>
);

/* -------------------------------------------------------------- type cards */

export const Kicker: React.FC<{ children: React.ReactNode; colour?: string }> = ({
  children,
  colour = C.accentSoft,
}) => (
  <div
    style={{
      fontFamily: MONO,
      fontWeight: 600,
      fontSize: 22,
      letterSpacing: "0.22em",
      textTransform: "uppercase",
      color: colour,
    }}
  >
    {children}
  </div>
);

/** Big statement type, revealed line by line. */
export const Statement: React.FC<{
  lines: React.ReactNode[];
  frame: number;
  start?: number;
  size?: number;
  align?: "left" | "center";
}> = ({ lines, frame, start = 0, size = 76, align = "left" }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
    {lines.map((l, i) => {
      const t = ease(frame, [start + i * 7, start + i * 7 + 26], [0, 1]);
      return (
        <div key={i} style={{ overflow: "hidden", paddingBottom: 4 }}>
          <div
            style={{
              fontFamily: FONT,
              fontWeight: 600,
              fontSize: size,
              lineHeight: 1.16,
              letterSpacing: "-0.03em",
              color: C.text1,
              textAlign: align,
              opacity: t,
              transform: `translateY(${(1 - t) * 44}px)`,
            }}
          >
            {l}
          </div>
        </div>
      );
    })}
  </div>
);

/** Count-up for a real measured number. */
export const Metric: React.FC<{
  value: number;
  suffix?: string;
  decimals?: number;
  label: string;
  frame: number;
  start: number;
  colour?: string;
}> = ({ value, suffix = "", decimals = 0, label, frame, start, colour = C.text1 }) => {
  const t = ease(frame, [start, start + 34], [0, 1]);
  const shown = (value * t).toFixed(decimals);
  return (
    <div style={{ opacity: ease(frame, [start, start + 12], [0, 1]) }}>
      <div
        style={{
          fontFamily: FONT,
          fontWeight: 600,
          fontSize: 82,
          letterSpacing: "-0.035em",
          color: colour,
          fontVariantNumeric: "tabular-nums",
          lineHeight: 1,
        }}
      >
        {shown}
        {suffix}
      </div>
      <div
        style={{
          fontFamily: FONT,
          fontSize: 22,
          color: C.text3,
          marginTop: 12,
          letterSpacing: "-0.005em",
        }}
      >
        {label}
      </div>
    </div>
  );
};

/** The engine's own wordmark, used on the open and close cards. */
export const Wordmark: React.FC<{ frame: number; start?: number }> = ({ frame, start = 0 }) => {
  const t = ease(frame, [start, start + 30], [0, 1]);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 18, opacity: t }}>
      <div
        style={{
          width: 46,
          height: 46,
          borderRadius: 10,
          border: `2px solid ${C.accent}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: `0 0 34px ${C.accent}66`,
        }}
      >
        <div
          style={{
            width: 16,
            height: 16,
            borderRadius: 4,
            backgroundColor: C.accent,
            transform: `rotate(${ease(frame, [start, start + 46], [0, 45])}deg)`,
          }}
        />
      </div>
      <span
        style={{
          fontFamily: FONT,
          fontWeight: 600,
          fontSize: 40,
          letterSpacing: "-0.02em",
          color: C.text1,
        }}
      >
        prahari
      </span>
      <span
        style={{
          fontFamily: MONO,
          fontSize: 22,
          color: C.text3,
          letterSpacing: "0.1em",
          paddingTop: 6,
        }}
      >
        प्रहरी
      </span>
    </div>
  );
};

export { FULL };
