import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { COLORS, FONT } from "./brand";

const MONO =
  'ui-monospace, "SF Mono", Menlo, monospace';

/**
 * 14s cold open. A dark room's ambience, told in data: a timestamp,
 * a dollar counter that starts as a whisper and accelerates into a scream,
 * and a burn line climbing across the frame. Ends on a hard beat.
 */
export const ColdOpen: React.FC = () => {
  const frame = useCurrentFrame();

  // Timestamp flickers on like a monitor waking.
  const tsFlicker =
    frame < 8 ? 0 : frame < 12 ? (frame % 2 === 0 ? 0.8 : 0.2) : 1;

  // The counter: slow creep, then compounding acceleration. $0.47 → $847.
  const spend = interpolate(frame, [20, 540], [0.47, 847.23], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });
  const spendStr = spend.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  // Counter turns from off-white to orange as the burn accelerates.
  const heat = interpolate(frame, [300, 510], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const counterColor = heat < 0.5 ? COLORS.offWhite : COLORS.orangeSoft;
  const counterScale = 1 + heat * 0.06 + (frame > 340 ? 0.02 : 0);

  // Burn line: deterministic jagged climb across the lower third.
  const points: string[] = [];
  const drawn = interpolate(frame, [30, 560], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.quad),
  });
  const N = 60;
  for (let i = 0; i <= Math.floor(N * drawn); i++) {
    const x = (i / N) * 1920;
    const progress = i / N;
    const wobble = Math.sin(i * 1.7) * 14 + Math.sin(i * 0.6) * 22;
    const y = 1010 - progress * progress * 320 - wobble * progress;
    points.push(`${x},${y}`);
  }

  // Label fades in under the counter.
  const labelIn = interpolate(frame, [50, 75], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Final beat: cut to black in the last 10 frames.
  const blackout = interpolate(frame, [588, 598], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: "#050810", fontFamily: FONT }}>
      {/* faint vignette pulse, like a heartbeat */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.65) 100%)",
          opacity: 0.8 + Math.sin(frame / 14) * 0.2,
        }}
      />

      {/* timestamp, top-left like a security feed */}
      <div
        style={{
          position: "absolute",
          top: 70,
          left: 90,
          fontFamily: MONO,
          fontSize: 44,
          letterSpacing: "0.12em",
          color: COLORS.inkMuted,
          opacity: tsFlicker,
        }}
      >
        03:04 AM
      </div>
      <div
        style={{
          position: "absolute",
          top: 70,
          right: 90,
          fontFamily: MONO,
          fontSize: 30,
          letterSpacing: "0.12em",
          color: "#3a4658",
          opacity: tsFlicker,
        }}
      >
        NOBODY WATCHING
      </div>

      {/* the burn counter */}
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 22,
          paddingBottom: 120,
        }}
      >
        <div
          style={{
            fontFamily: MONO,
            fontSize: 170,
            fontWeight: 700,
            fontVariantNumeric: "tabular-nums",
            color: counterColor,
            transform: `scale(${counterScale})`,
            textShadow:
              heat > 0.3
                ? `0 0 ${40 * heat}px rgba(234,88,12,${0.45 * heat})`
                : "none",
          }}
        >
          ${spendStr}
        </div>
        <div
          style={{
            fontSize: 32,
            fontWeight: 600,
            letterSpacing: "0.22em",
            color: "#4b5a72",
            opacity: labelIn,
          }}
        >
          AGENT SPEND SINCE MIDNIGHT
        </div>
      </AbsoluteFill>

      {/* the climbing burn line */}
      {points.length > 1 && (
        <svg
          width={1920}
          height={1080}
          style={{ position: "absolute", inset: 0 }}
        >
          <polyline
            points={points.join(" ")}
            fill="none"
            stroke={COLORS.orange}
            strokeWidth={5}
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity={0.9}
            style={{
              filter: `drop-shadow(0 0 ${8 + heat * 18}px rgba(234,88,12,0.7))`,
            }}
          />
        </svg>
      )}

      <AbsoluteFill style={{ background: "#000", opacity: blackout }} />
    </AbsoluteFill>
  );
};
