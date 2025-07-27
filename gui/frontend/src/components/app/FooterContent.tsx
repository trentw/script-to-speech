import { UniversalAudioPlayer } from '../UniversalAudioPlayer';

export const FooterContent = () => {
  return (
    <div className="border-border bg-background/95 supports-[backdrop-filter]:bg-background/60 border-t backdrop-blur">
      <div className="p-4">
        <UniversalAudioPlayer />
      </div>
    </div>
  );
};
