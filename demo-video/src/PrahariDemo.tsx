import React from "react";
import {
  AbsoluteFill,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;

/** ~105 seconds — judge-friendly, matches DEMO_SCRIPT_90s.md beats */
const SCENE_SEC = [8, 18, 22, 18, 18, 14, 7] as const;
export const TOTAL_FRAMES = SCENE_SEC.reduce((a, b) => a + b, 0) * FPS;

type Scene = {
  id: string;
  seconds: number;
  image?: string;
  kicker: string;
  title: string;
  line: string;
  badge?: string;
};

const SCENES: Scene[] = [
  {
    id: "open",
    seconds: SCENE_SEC[0],
    kicker: "SIH26165 · Oil India Limited",
    title: "prahari · प्रहरी",
    line: "Most safety systems rank what happened.\nThis one ranks what almost did.",
    badge: "100% OFFLINE",
  },
  {
    id: "thesis",
    seconds: SCENE_SEC[1],
    image: "screenshots/01-triage-thesis.png",
    kicker: "Control room",
    title: "Potential ≠ severity",
    line: "We rank high energy + missing barrier — not what bled.\nNeuro-symbolic · every verdict cites a named rule.",
    badge: "Engine online",
  },
  {
    id: "report-a",
    seconds: SCENE_SEC[2],
    image: "screenshots/01-triage-psif-live.png",
    kicker: "Live Analysis · Report A",
    title: "Cut finger in the workshop",
    line: "Real injury. First aid. Everyone tracks this.\nVerdict: LOW SIF potential — energy could never kill him.",
    badge: "low_severity",
  },
  {
    id: "report-b",
    seconds: SCENE_SEC[3],
    image: "screenshots/05-live-analysis-psif.png",
    kicker: "Live Analysis · Report B",
    title: "Guard missing · not isolated · no injury",
    line: "Nothing happened. Closed the same day anywhere else.\nVerdict: POTENTIAL SIF · Life-Saving Rule: Energy Isolation.",
    badge: "PSIF",
  },
  {
    id: "detail",
    seconds: SCENE_SEC[4],
    image: "screenshots/03-report-detail.png",
    kicker: "Explainability",
    title: "Every verdict is a receipt",
    line: "Named rules + character spans highlighted inline.\nDefendable to a union rep, a regulator, and the crew.",
    badge: "Rule-traced",
  },
  {
    id: "map",
    seconds: SCENE_SEC[5],
    image: "screenshots/02-precursor-map.png",
    kicker: "Patterns",
    title: "Precursor Accumulation Index",
    line: "One report is noise.\nThe same barrier failing again at the same site is the signal.",
    badge: "Site × energy",
  },
  {
    id: "close",
    seconds: SCENE_SEC[6],
    image: "screenshots/04-life-saving-rules.png",
    kicker: "IOGP Report 459",
    title: "Built for OIL field conditions",
    line: "Multilingual NLP extracts facts. Rules decide. Fully offline.\nSIH26165 · prahari",
    badge: "Win the demo",
  },
];

const COLORS = {
  bg: "#0B0F14",
  card: "#131A22",
  border: "#243040",
  ink: "#E6EDF3",
  muted: "#9FB0C0",
  accent: "#0f62fe",
  serious: "#ec835a",
  good: "#0ca30c",
};

const FadeSlide: React.FC<{ children: React.ReactNode; delay?: number }> = ({
  children,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = spring({
    frame: frame - delay,
    fps,
    config: { damping: 200 },
  });
  const opacity = interpolate(t, [0, 1], [0, 1], { extrapolateRight: "clamp" });
  const y = interpolate(t, [0, 1], [24, 0], { extrapolateRight: "clamp" });
  return <div style={{ opacity, transform: `translateY(${y}px)` }}>{children}</div>;
};

const SceneFrame: React.FC<{ scene: Scene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 8, durationInFrames - 1],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const fadeIn = interpolate(frame, [0, 10], [0, 1], {
    extrapolateRight: "clamp",
  });
  const zoom = interpolate(frame, [0, durationInFrames], [1, 1.04], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg, opacity: fadeIn * fadeOut }}>
      {scene.image ? (
        <AbsoluteFill>
          <Img
            src={staticFile(scene.image)}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              objectPosition: "top center",
              transform: `scale(${zoom})`,
            }}
          />
          <AbsoluteFill
            style={{
              background:
                "linear-gradient(180deg, rgba(11,15,20,0.55) 0%, rgba(11,15,20,0.25) 35%, rgba(11,15,20,0.88) 72%, rgba(11,15,20,0.96) 100%)",
            }}
          />
        </AbsoluteFill>
      ) : (
        <AbsoluteFill
          style={{
            background:
              "radial-gradient(ellipse at 30% 20%, #1a2740 0%, #0B0F14 55%)",
          }}
        />
      )}

      <AbsoluteFill
        style={{
          justifyContent: "flex-end",
          padding: "64px 72px",
        }}
      >
        <FadeSlide>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 12,
              marginBottom: 18,
            }}
          >
            <span
              style={{
                fontSize: 22,
                letterSpacing: 2,
                textTransform: "uppercase",
                color: COLORS.accent,
                fontWeight: 600,
              }}
            >
              {scene.kicker}
            </span>
            {scene.badge && (
              <span
                style={{
                  fontSize: 18,
                  fontWeight: 600,
                  color: COLORS.ink,
                  backgroundColor: "rgba(15,98,254,0.2)",
                  border: `1px solid ${COLORS.accent}`,
                  borderRadius: 4,
                  padding: "4px 12px",
                }}
              >
                {scene.badge}
              </span>
            )}
          </div>
          <h1
            style={{
              margin: 0,
              fontSize: scene.image ? 56 : 72,
              fontWeight: 700,
              color: COLORS.ink,
              letterSpacing: -1,
              lineHeight: 1.15,
              maxWidth: 1400,
            }}
          >
            {scene.title}
          </h1>
          <p
            style={{
              margin: "18px 0 0",
              fontSize: 30,
              lineHeight: 1.45,
              color: COLORS.muted,
              whiteSpace: "pre-line",
              maxWidth: 1320,
              fontWeight: 400,
            }}
          >
            {scene.line}
          </p>
        </FadeSlide>
      </AbsoluteFill>

      <div
        style={{
          position: "absolute",
          top: 36,
          left: 72,
          display: "flex",
          alignItems: "center",
          gap: 14,
        }}
      >
        <div
          style={{
            width: 18,
            height: 18,
            borderRadius: 999,
            backgroundColor: COLORS.good,
            boxShadow: `0 0 16px ${COLORS.good}`,
          }}
        />
        <span style={{ fontSize: 22, color: COLORS.ink, fontWeight: 600 }}>
          prahari
        </span>
        <span style={{ fontSize: 18, color: COLORS.muted }}>SIH26165</span>
      </div>
    </AbsoluteFill>
  );
};

export const PrahariDemo: React.FC = () => {
  let from = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg }}>
      {SCENES.map((scene) => {
        const durationInFrames = scene.seconds * FPS;
        const start = from;
        from += durationInFrames;
        return (
          <Sequence key={scene.id} from={start} durationInFrames={durationInFrames}>
            <SceneFrame scene={scene} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
