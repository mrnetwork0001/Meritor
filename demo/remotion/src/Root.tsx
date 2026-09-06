import { Composition } from "remotion";
import { Meritor, FPS, DURATION_S } from "./Meritor";

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Meritor"
    component={Meritor}
    durationInFrames={Math.round(DURATION_S * FPS)}
    fps={FPS}
    width={1920}
    height={1080}
  />
);
