import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  Loop,
  OffthreadVideo,
  Sequence,
  staticFile,
  interpolate,
  useCurrentFrame,
} from "remotion";

type Subtitle = {
  text: string;
  startFrame: number;
  durationFrames: number;
};

type Scene = {
  sceneId: string;
  objective: string;
  durationFrames: number;
  startFrame: number;
  card: string;
  audio: string;
  background: string | null;
  backgroundImage?: string | null;
  backgroundLoopFrames: number;
  visualPrompt?: {
    visual_style?: string;
    motion_direction?: string;
    on_screen_emphasis?: string[];
  };
  subtitles: Subtitle[];
};

export type ShortsJob = {
  scriptId: string;
  fps: number;
  width: number;
  height: number;
  durationFrames: number;
  subtitleCenterRatio?: number;
  scenes: Scene[];
};

const highlightColor = "#ffd43b";

const headlineByObjective: Record<string, string[]> = {
  hook: ["월 100만원 배당?", "JEPI·JEPQ 전에", "이것부터 보세요"],
  mechanism: ["월분배 ETF", "돈 나오는 구조는", "커버드콜"],
  comparison: ["SCHD는", "월급보다", "배당의 질"],
  tradeoff: ["이름보다", "목적이 먼저", "현금흐름 vs 성장"],
  risk: ["높은 분배금", "공짜가 아닙니다", "원금도 흔들림"],
  close: ["ETF 선택", "수익률보다", "내 목표부터"],
};

const yellowWords = [
  "월",
  "100만원",
  "배당",
  "JEPI",
  "JEPQ",
  "SCHD",
  "커버드콜",
  "목적",
  "현금흐름",
  "성장",
  "공짜",
  "원금",
  "목표",
];

const subtitleBox: React.CSSProperties = {
  position: "absolute",
  left: "5.4%",
  right: "5.4%",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  minHeight: 118,
  padding: "20px 34px",
  borderRadius: 22,
  background: "#ffffff",
  boxShadow: "0 16px 0 rgba(0, 0, 0, 0.85), 0 24px 48px rgba(0, 0, 0, 0.5)",
  border: "4px solid #111111",
};

const subtitleText: React.CSSProperties = {
  color: "#050505",
  fontFamily: "'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif",
  fontSize: 45,
  fontWeight: 900,
  lineHeight: 1.14,
  textAlign: "center",
  textShadow: "none",
  wordBreak: "keep-all",
};

const getHeadline = (scene: Scene): string[] => {
  const fixed = headlineByObjective[scene.objective];
  if (fixed) {
    return fixed;
  }

  const emphasis = scene.visualPrompt?.on_screen_emphasis ?? [];
  return emphasis.length > 0 ? emphasis.slice(0, 3) : [scene.subtitles[0]?.text ?? ""];
};

const renderHighlightedLine = (line: string) => {
  const parts = line.split(/(JEPI|JEPQ|SCHD|100만원|월|배당|커버드콜|목적|현금흐름|성장|공짜|원금|목표)/g);
  return parts.map((part, index) => (
    <span
      key={part + index}
      style={{color: yellowWords.includes(part) ? highlightColor : "#ffffff"}}
    >
      {part}
    </span>
  ));
};

const SceneView: React.FC<{scene: Scene; subtitleCenterRatio: number}> = ({scene, subtitleCenterRatio}) => {
  const frame = useCurrentFrame();
  const progress = Math.min(1, Math.max(0, frame / Math.max(1, scene.durationFrames - 1)));
  const zoom = interpolate(progress, [0, 1], [1.02, 1.11]);
  const slide = interpolate(progress, [0, 1], [0, -18]);
  const fadeIn = interpolate(frame, [0, 10], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp"});
  const headline = getHeadline(scene);
  const boxStyle: React.CSSProperties = {
    ...subtitleBox,
    top: `${subtitleCenterRatio * 100}%`,
    transform: "translateY(-50%)",
  };

  return (
    <AbsoluteFill style={{backgroundColor: "#000000"}}>
      <div
        style={{
          position: "absolute",
          top: 38,
          left: 46,
          right: 46,
          height: 536,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          gap: 12,
          textAlign: "center",
          fontFamily: "'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif",
          fontWeight: 950,
          lineHeight: 1.03,
          letterSpacing: 0,
          textShadow: "0 7px 0 rgba(0,0,0,0.95), 0 12px 24px rgba(0,0,0,0.75)",
        }}
      >
        {headline.map((line, index) => (
          <div
            key={line + index}
            style={{
              fontSize: line.length > 12 ? 70 : 82,
              maxWidth: "100%",
              whiteSpace: "normal",
              wordBreak: "keep-all",
            }}
          >
            {renderHighlightedLine(line)}
          </div>
        ))}
      </div>

      <div
        style={{
          position: "absolute",
          top: 604,
          left: 0,
          right: 0,
          height: 738,
          overflow: "hidden",
          borderTop: "6px solid #111111",
          borderBottom: "6px solid #111111",
          background: "#151515",
        }}
      >
      {scene.background ? (
        <Loop durationInFrames={scene.backgroundLoopFrames}>
          <OffthreadVideo
            src={staticFile(scene.background)}
            muted
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              transform: `scale(${zoom}) translateY(${slide}px)`,
              filter: "saturate(0.92) contrast(1.08) brightness(0.9)",
            }}
          />
        </Loop>
      ) : scene.backgroundImage ? (
        <Img
          src={staticFile(scene.backgroundImage)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${zoom}) translateY(${slide}px)`,
            filter: "saturate(0.92) contrast(1.08) brightness(0.9)",
          }}
        />
      ) : (
        <Img
          src={staticFile(scene.card)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${zoom}) translateY(${slide}px)`,
          }}
        />
      )}
        <AbsoluteFill
          style={{
            background:
              "linear-gradient(180deg, rgba(0,0,0,0.12) 0%, rgba(0,0,0,0) 44%, rgba(0,0,0,0.22) 100%)",
          }}
        />
      </div>

      <Audio src={staticFile(scene.audio)} />

      {scene.subtitles.map((subtitle, idx) => (
        <Sequence
          key={scene.sceneId + "-" + idx}
          from={subtitle.startFrame}
          durationInFrames={subtitle.durationFrames}
        >
          <div style={{...boxStyle, opacity: fadeIn}}>
            <div style={subtitleText}>{subtitle.text}</div>
          </div>
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

export const ShortsVideo: React.FC<ShortsJob> = ({scenes, subtitleCenterRatio = 0.52}) => {
  return (
    <AbsoluteFill style={{backgroundColor: "#101923"}}>
      {scenes.map((scene) => (
        <Sequence
          key={scene.sceneId}
          from={scene.startFrame}
          durationInFrames={scene.durationFrames}
        >
          <SceneView scene={scene} subtitleCenterRatio={subtitleCenterRatio} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
