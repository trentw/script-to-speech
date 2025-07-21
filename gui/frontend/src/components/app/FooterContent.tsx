import { useCentralAudio } from '../../stores/appStore';
import { UniversalAudioPlayer } from '../UniversalAudioPlayer';

export const FooterContent = () => {
  const {
    audioUrl,
    primaryText,
    secondaryText,
    downloadFilename,
    loading: audioLoading,
    autoplay,
  } = useCentralAudio();

  return (
    <div className="border-border bg-background/95 supports-[backdrop-filter]:bg-background/60 border-t backdrop-blur">
      <div className="p-4">
        <UniversalAudioPlayer
          audioUrl={audioUrl}
          primaryText={primaryText}
          secondaryText={secondaryText}
          downloadFilename={downloadFilename}
          loading={audioLoading}
          autoplay={autoplay}
        />
      </div>
    </div>
  );
};
