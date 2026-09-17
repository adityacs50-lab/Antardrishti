import React from "react";
import { Composition } from "remotion";
import { PrahariDemo, TOTAL_FRAMES, FPS, WIDTH, HEIGHT } from "./PrahariDemo";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="PrahariDemo"
      component={PrahariDemo}
      durationInFrames={TOTAL_FRAMES}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
    />
  );
};
