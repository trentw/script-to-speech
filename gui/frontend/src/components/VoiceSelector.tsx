import React from 'react';
import { Button } from '@/components/ui/button';
import { ChevronRight, Volume2 } from 'lucide-react';
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
  onVoiceSelect,
  onOpenVoicePanel
}) => {
  const getVoiceDisplayName = (voice: VoiceEntry) => {
    return voice.description?.provider_name || voice.sts_id;
  };

  if (!voices || voices.length === 0) {
    return (
      <div className="text-center py-6 text-muted-foreground">
        <Volume2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No voices available for {provider}</p>
        <p className="text-xs mt-1 opacity-75">
          Configure provider settings manually below
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <Button
        variant="outline"
        className="w-full justify-between h-auto p-3 hover:bg-accent hover:text-accent-foreground transition-all duration-200 hover:border-accent"
        onClick={onOpenVoicePanel}
      >
        <div className="flex items-center gap-3">
          {/* Voice info */}
          <div className="text-left">
            <div className="font-medium">
              {selectedVoice ? getVoiceDisplayName(selectedVoice) : 'Select a voice'}
            </div>
            {selectedVoice && (
              <div className="text-xs text-muted-foreground">
                {selectedVoice.voice_properties?.gender && selectedVoice.voice_properties.accent 
                  ? `${selectedVoice.voice_properties.gender} • ${selectedVoice.voice_properties.accent}`
                  : selectedVoice.description?.custom_description?.slice(0, 40) + '...'
                }
              </div>
            )}
          </div>
        </div>
        
        <ChevronRight className="h-4 w-4 opacity-50 shrink-0" />
      </Button>

      {/* Selected voice details */}
      {selectedVoice?.description?.custom_description && (
        <div className="text-xs text-muted-foreground bg-muted/30 rounded-lg p-3">
          {selectedVoice.description.custom_description}
        </div>
      )}
    </div>
  );
};