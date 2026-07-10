import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { COLORS, FONT } from "./brand";
import { Logo } from "./Logo";

/** 7s closing card: logo, tagline punch, repo URL, hackathon footer. */
export const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const line1 = interpolate(frame, [24, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const line2 = spring({
    frame: frame - 44,
    fps,
    config: { damping: 10, stiffness: 140 },
  });
  const urlIn = interpolate(frame, [70, 86], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const footIn = interpolate(frame, [88, 104], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(frame, [196, 210], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{ background: COLORS.dark, fontFamily: FONT, opacity: fadeOut }}
    >
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 34,
        }}
      >
        <Logo size={190} lineColor={COLORS.offWhite} startFrame={0} />
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              fontSize: 62,
              fontWeight: 700,
              letterSpacing: "-0.02em",
              color: COLORS.offWhite,
              opacity: line1,
              transform: `translateY(${(1 - line1) * 20}px)`,
            }}
          >
            Token counts don't pay the bill.
          </div>
          <div
            style={{
              fontSize: 84,
              fontWeight: 800,
              letterSpacing: "-0.025em",
              color: COLORS.orange,
              marginTop: 10,
              opacity: Math.min(1, line2),
              transform: `scale(${0.8 + Math.min(1, line2) * 0.2})`,
            }}
          >
            Dollars do.
          </div>
        </div>
        <div
          style={{
            fontSize: 40,
            fontWeight: 600,
            color: COLORS.offWhite,
            border: `2px solid ${COLORS.darkBorder}`,
            borderRadius: 100,
            padding: "16px 42px",
            opacity: urlIn,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          github.com/siddhardh-7/BurnRate
        </div>
        <div
          style={{
            fontSize: 28,
            fontWeight: 600,
            color: COLORS.inkMuted,
            opacity: footIn,
          }}
        >
          Built on <span style={{ color: COLORS.orangeSoft }}>SigNoz</span> · Agents of SigNoz Hackathon 2026
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
