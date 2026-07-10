import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { COLORS, FONT } from "./brand";
import { Logo } from "./Logo";

/** 5s title card: gridlines, budget line, logo draw-in, wordmark, tagline. */
export const Intro: React.FC = () => {
  const frame = useCurrentFrame();

  const barScale = interpolate(frame, [0, 10], [0, 1], {
    extrapolateRight: "clamp",
  });
  const wordmarkIn = interpolate(frame, [52, 70], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const taglineIn = interpolate(frame, [70, 88], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(frame, [138, 150], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: COLORS.white, fontFamily: FONT }}>
      {/* top gradient bar */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 14,
          background: `linear-gradient(90deg, ${COLORS.amber}, ${COLORS.orange})`,
          transform: `scaleX(${barScale})`,
          transformOrigin: "left",
        }}
      />
      {/* faint dashboard gridlines */}
      {[260, 460, 660, 860].map((y) => (
        <div
          key={y}
          style={{
            position: "absolute",
            top: y,
            left: 0,
            right: 0,
            height: 2,
            background: COLORS.grid,
          }}
        />
      ))}
      {/* dashed budget threshold */}
      <div
        style={{
          position: "absolute",
          top: 210,
          left: 0,
          right: 0,
          borderTop: `3px dashed #fed7aa`,
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 168,
          right: 100,
          fontSize: 26,
          fontWeight: 600,
          letterSpacing: "0.05em",
          color: "#fdba74",
        }}
      >
        BUDGET
      </div>

      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 36,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 44 }}>
          <Logo size={250} lineColor={COLORS.ink} startFrame={8} />
          <div
            style={{
              fontSize: 156,
              fontWeight: 800,
              letterSpacing: "-0.035em",
              color: COLORS.ink,
              opacity: wordmarkIn,
              transform: `translateY(${(1 - wordmarkIn) * 26}px)`,
            }}
          >
            Burnrate
          </div>
        </div>
        <div
          style={{
            fontSize: 44,
            fontWeight: 500,
            color: COLORS.inkMid,
            letterSpacing: "-0.01em",
            opacity: taglineIn,
            transform: `translateY(${(1 - taglineIn) * 18}px)`,
          }}
        >
          Real-time <span style={{ color: COLORS.orange, fontWeight: 700 }}>dollar costs</span> for AI agents — on every OpenTelemetry span.
        </div>
      </AbsoluteFill>

      {/* fade to dark so the first chapter card cuts cleanly */}
      <AbsoluteFill style={{ background: COLORS.dark, opacity: fadeOut }} />
    </AbsoluteFill>
  );
};
