import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { CHAPTERS, COLORS, FONT } from "./brand";

/** 1.2s chapter card: dark slate, orange index, title, progress bar. */
export const ChapterCard: React.FC<{ chapter: number }> = ({ chapter }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { index, title } = CHAPTERS[chapter - 1];

  const fadeIn = interpolate(frame, [0, 4], [0, 1], {
    extrapolateRight: "clamp",
  });
  const numIn = spring({ frame, fps, config: { damping: 14, stiffness: 160 } });
  const titleIn = spring({
    frame: frame - 4,
    fps,
    config: { damping: 14, stiffness: 160 },
  });
  const barWidth = interpolate(
    frame,
    [6, 24],
    [((chapter - 1) / 5) * 100, (chapter / 5) * 100],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 4, durationInFrames],
    [1, 0.85],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        background: COLORS.dark,
        fontFamily: FONT,
        opacity: fadeIn * fadeOut,
      }}
    >
      {/* faint grid */}
      {[270, 540, 810].map((y) => (
        <div
          key={y}
          style={{
            position: "absolute",
            top: y,
            left: 0,
            right: 0,
            height: 1,
            background: COLORS.gridDark,
          }}
        />
      ))}
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          gap: 10,
        }}
      >
        <div
          style={{
            fontSize: 54,
            fontWeight: 700,
            letterSpacing: "0.28em",
            color: COLORS.orange,
            fontVariantNumeric: "tabular-nums",
            opacity: numIn,
            transform: `translateY(${(1 - numIn) * 30}px)`,
          }}
        >
          {index}
        </div>
        <div
          style={{
            fontSize: 120,
            fontWeight: 800,
            letterSpacing: "-0.03em",
            color: COLORS.offWhite,
            opacity: titleIn,
            transform: `translateY(${(1 - titleIn) * 30}px)`,
          }}
        >
          {title}
        </div>
      </AbsoluteFill>
      {/* chapter progress bar */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          height: 10,
          width: `${barWidth}%`,
          background: `linear-gradient(90deg, ${COLORS.amber}, ${COLORS.orange})`,
        }}
      />
    </AbsoluteFill>
  );
};
