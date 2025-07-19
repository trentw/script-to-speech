
import { UniversalAudioPlayer } from '../UniversalAudioPlayer';
import { useCentralAudio } from '../../stores/appStore';

export const FooterContent = ({ isGenerating: _isGenerating }: { isGenerating: boolean }) => {
  const { audioUrl, primaryText, secondaryText, downloadFilename, loading: audioLoading, autoplay } = useCentralAudio();

  return (
    <div className="border-t border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
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
