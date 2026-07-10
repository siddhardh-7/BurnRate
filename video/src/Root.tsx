import React from "react";
import { Composition } from "remotion";
import { ChapterCard } from "./ChapterCard";
import { Intro } from "./Intro";
import { Outro } from "./Outro";

const FPS = 30;
const W = 1920;
const H = 1080;
const CARD_FRAMES = 36; // 1.2s

export const Root: React.FC = () => (
  <>
    <Composition
      id="Intro"
      component={Intro}
      durationInFrames={150}
      fps={FPS}
      width={W}
      height={H}
    />
    {[1, 2, 3, 4, 5].map((n) => (
      <Composition
        key={n}
        id={`Card0${n}`}
        component={ChapterCard}
        durationInFrames={CARD_FRAMES}
        fps={FPS}
        width={W}
        height={H}
        defaultProps={{ chapter: n }}
      />
    ))}
    <Composition
      id="Outro"
      component={Outro}
      durationInFrames={210}
      fps={FPS}
      width={W}
      height={H}
    />
  </>
);
