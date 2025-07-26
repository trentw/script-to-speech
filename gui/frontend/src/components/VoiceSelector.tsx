import { Volume2 } from 'lucide-react';
import React from 'react';

import { SelectorButton, SelectorDetailsView } from '@/components/ui/selector';
import { getVoiceDisplayName, getVoiceSubtext } from '@/utils/voiceUtils';

import type { VoiceEntry } from '../types';

interface VoiceSelectorProps {
  provider: string;
  voices: VoiceEntry[];
  selectedVoice?: VoiceEntry;
  onVoiceSelect: (voice: VoiceEntry) => void;
  onOpenVoicePanel: () => void;
}

export const VoiceSelector: React.FC<VoiceSelectorProps> = ({
  provider,
  voices,
  selectedVoice,
  onVoiceSelect: _onVoiceSelect,
  onOpenVoicePanel,
}) => {

  const renderVoiceTags = (voice: VoiceEntry) => {
    const tags: Array<{
      label: string;
      variant: 'default' | 'secondary' | 'outline';
    }> = [];

    // Character types
    if (voice.tags?.character_types) {
      voice.tags.character_types.slice(0, 2).forEach((type) => {
        tags.push({ label: type, variant: 'secondary' as const });
      });
    }

    // Custom tags
    if (voice.tags?.custom_tags) {
      voice.tags.custom_tags.slice(0, 3).forEach((tag) => {
        tags.push({ label: tag, variant: 'outline' as const });
      });
    }

    return tags;
  };

  if (!voices || voices.length === 0) {
    return (
      <div className="space-y-3">
        <div className="text-muted-foreground py-8 text-center">
          <div className="bg-muted/30 mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full">
            <Volume2 className="h-6 w-6 opacity-50" />
          </div>
          <p className="text-sm font-medium">
            No preconfigured voices available for {provider}
          </p>
          <p className="mt-1 text-xs opacity-75">
            Check your API configuration or configure settings manually below
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <SelectorButton
        selectedItem={selectedVoice}
        placeholder="Select voice"
        onClick={onOpenVoicePanel}
        renderPrimary={getVoiceDisplayName}
        renderSecondary={(voice) =>
          getVoiceSubtext(voice) ||
          voice.description?.custom_description?.slice(0, 35) + '...'
        }
        availableCount={voices.length}
      />

      <SelectorDetailsView
        selectedItem={selectedVoice}
        renderDescription={(voice) =>
          voice.description?.custom_description || ''
        }
        renderTags={renderVoiceTags}
      />
    </div>
  );
};
