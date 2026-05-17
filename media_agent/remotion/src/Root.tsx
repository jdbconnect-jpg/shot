import React from "react";
import {Composition, getInputProps} from "remotion";
import {ShortsVideo, type ShortsJob} from "./ShortsVideo";
import fallbackJob from "../public/shorts-job.json";

export const RemotionRoot: React.FC = () => {
  const inputProps = getInputProps() as Partial<ShortsJob>;
  const job = {
    ...(fallbackJob as ShortsJob),
    ...inputProps,
  };

  return (
    <Composition
      id="ShortsVideo"
      component={ShortsVideo}
      durationInFrames={job.durationFrames}
      fps={job.fps}
      width={job.width}
      height={job.height}
      defaultProps={job}
    />
  );
};
