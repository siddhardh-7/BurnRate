import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "./brand";

/**
 * The Burnrate mark, animated: the cost line draws in from the left,
 * then the flame pops at the spike with a springy overshoot and the
 * amber core flickers gently.
 */
export const Logo: React.FC<{
  size: number;
  lineColor: string;
  startFrame?: number;
}> = ({ size, lineColor, startFrame = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = Math.max(0, frame - startFrame);

  // The line path is ~43 units long; 50 covers it with margin.
  const LINE_LEN = 50;
  const drawn = interpolate(t, [0, 32], [LINE_LEN, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const flameScale = spring({
    frame: t - 26,
    fps,
    config: { damping: 9, stiffness: 120, mass: 0.6 },
  });

  // Subtle flicker on the amber core once the flame is up.
  const flicker =
    t > 40 ? 1 + Math.sin(t / 2.4) * 0.06 : Math.min(1, flameScale);

  return (
    <svg width={size} height={size} viewBox="0 0 64 64">
      <path
        d="M8,52 L20,50.5 L29,47 L36,40 L42,31"
        fill="none"
        stroke={lineColor}
        strokeWidth={4.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={LINE_LEN}
        strokeDashoffset={drawn}
      />
      <g
        transform={`translate(46, 23) scale(${flameScale}) translate(-46, -23)`}
      >
        <path
          d="M46,8 C49.5,13 55,16.5 55,23 a9,9 0 1 1 -18,0 C37,16.5 42.5,13 46,8 Z"
          fill={COLORS.orange}
        />
        <g
          transform={`translate(46, 22) scale(${flicker}) translate(-46, -22)`}
        >
          <path
            d="M46,17.5 C47.8,20 50,21.5 50,24.5 a4,4 0 1 1 -8,0 C42,21.5 44.2,20 46,17.5 Z"
            fill={COLORS.amber}
          />
        </g>
      </g>
    </svg>
  );
};
