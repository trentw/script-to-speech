import React from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ChevronRight, Volume2, User } from 'lucide-react';
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
  onVoiceSelect: _onVoiceSelect, // Not used directly in this component
  onOpenVoicePanel
}) => {
  const getVoiceDisplayName = (voice: VoiceEntry) => {
    return voice.description?.provider_name || voice.sts_id;
  };

  const getVoiceSubtext = (voice: VoiceEntry) => {
    const parts = [];
    if (voice.voice_properties?.gender) parts.push(voice.voice_properties.gender);
    if (voice.voice_properties?.accent) parts.push(voice.voice_properties.accent);
    if (voice.description?.perceived_age) parts.push(voice.description.perceived_age);
    return parts.join(' • ');
  };

  if (!voices || voices.length === 0) {
    return (
      <div className="space-y-3">
        <div className="text-center py-8 text-muted-foreground">
          <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-muted/30 flex items-center justify-center">
            <Volume2 className="w-6 h-6 opacity-50" />
          </div>
          <p className="text-sm font-medium">No voices available for {provider}</p>
          <p className="text-xs mt-1 opacity-75">
            Check your API configuration or configure settings manually below
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <Button
        variant="outline"
        className="w-full h-auto p-0 hover:bg-accent hover:text-accent-foreground hover:border-accent transition-all duration-200 cursor-pointer"
        onClick={onOpenVoicePanel}
      >
        <div className="flex items-center justify-between w-full p-3">
          <div className="flex items-center gap-3">
            {/* Voice avatar placeholder */}
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm font-semibold">
              {selectedVoice ? (
                getVoiceDisplayName(selectedVoice).charAt(0).toUpperCase()
              ) : (
                <User className="w-4 h-4" />
              )}
            </div>
            
            {/* Voice info */}
            <div className="text-left">
              <div className="font-medium text-sm">
                {selectedVoice ? getVoiceDisplayName(selectedVoice) : 'Select voice'}
              </div>
              {selectedVoice ? (
                <div className="text-xs text-muted-foreground">
                  {getVoiceSubtext(selectedVoice) || selectedVoice.description?.custom_description?.slice(0, 35) + '...'}
                </div>
              ) : (
                <div className="text-xs text-muted-foreground">
                  Choose from {voices.length} available voice{voices.length !== 1 ? 's' : ''}
                </div>
              )}
            </div>
          </div>
          
          <ChevronRight className="h-4 w-4 opacity-50 shrink-0" />
        </div>
      </Button>

      {/* Enhanced voice details */}
      {selectedVoice && (
        <div className="bg-muted/30 rounded-lg p-3 space-y-2">
          {selectedVoice.description?.custom_description && (
            <p className="text-xs text-muted-foreground">
              {selectedVoice.description.custom_description}
            </p>
          )}
          
          {/* Character types and tags */}
          {(selectedVoice.tags?.character_types || selectedVoice.tags?.custom_tags) && (
            <div className="flex flex-wrap gap-1">
              {selectedVoice.tags?.character_types?.slice(0, 2).map((type, index) => (
                <Badge key={`char-${index}`} variant="secondary" className="text-xs px-1.5 py-0">
                  {type}
                </Badge>
              ))}
              {selectedVoice.tags?.custom_tags?.slice(0, 3).map((tag, index) => (
                <Badge key={`tag-${index}`} variant="outline" className="text-xs px-1.5 py-0">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};