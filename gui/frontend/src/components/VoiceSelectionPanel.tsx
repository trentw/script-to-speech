import { ArrowLeft, Search } from 'lucide-react';
import React, { useState } from 'react';

import { PlayPreviewButton } from '@/components/PlayPreviewButton';
import { Badge } from '@/components/ui/badge';
import { appButtonVariants } from '@/components/ui/button-variants';
import { getVoiceDisplayName, getVoiceSubtext } from '@/utils/voiceUtils';

import type { VoiceEntry } from '../types';

interface VoiceSelectionPanelProps {
  provider: string;
  voices: VoiceEntry[];
  selectedVoice?: VoiceEntry;
  onVoiceSelect: (voice: VoiceEntry) => void;
  onBack: () => void;
}

export const VoiceSelectionPanel: React.FC<VoiceSelectionPanelProps> = ({
  provider,
  voices,
  selectedVoice,
  onVoiceSelect,
  onBack,
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredVoices = voices.filter((voice) => {
    if (!searchQuery) return true;
    const name = getVoiceDisplayName(voice).toLowerCase();
    const subtext = getVoiceSubtext(voice).toLowerCase();
    const tags = voice.tags?.custom_tags?.join(' ').toLowerCase() || '';
    return (
      name.includes(searchQuery.toLowerCase()) ||
      subtext.includes(searchQuery.toLowerCase()) ||
      tags.includes(searchQuery.toLowerCase())
    );
  });

  return (
    <div className="bg-background flex h-full flex-col">
      {/* Header */}
      <div className="border-border flex items-center gap-3 border-b p-4">
        <button
          className={appButtonVariants({
            variant: 'list-action',
            size: 'icon-sm',
          })}
          onClick={onBack}
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <h3 className="font-medium">Select a voice</h3>
      </div>

      {/* Search */}
      <div className="border-border border-b p-4">
        <div className="relative">
          <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 transform" />
          <input
            type="text"
            placeholder="Search voices..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="border-border bg-background text-foreground placeholder:text-muted-foreground focus:ring-primary w-full rounded-md border py-2 pr-4 pl-10 focus:border-transparent focus:ring-2 focus:outline-none"
          />
        </div>
      </div>

      {/* Voice List */}
      <div className="flex-1 overflow-auto">
        <div className="p-4">
          <div className="space-y-1">
            <h4 className="text-muted-foreground mb-3 text-sm font-medium">
              {provider} Voices ({filteredVoices.length})
            </h4>

            {filteredVoices.length === 0 ? (
              <div className="text-muted-foreground py-8 text-center">
                <p className="text-sm">No voices found</p>
                <p className="mt-1 text-xs">Try adjusting your search</p>
              </div>
            ) : (
              <div className="space-y-2">
                {filteredVoices.map((voice) => (
                  <button
                    key={voice.sts_id}
                    className={`group relative w-full cursor-pointer rounded-lg border p-3 text-left transition-all duration-200 ${
                      selectedVoice?.sts_id === voice.sts_id
                        ? 'border-primary bg-accent text-accent-foreground shadow-sm'
                        : 'border-border hover:bg-accent hover:text-accent-foreground hover:border-accent hover:shadow-sm'
                    }`}
                    onClick={() => onVoiceSelect(voice)}
                  >
                    <div className="flex items-start gap-3">
                      {/* Voice info */}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between">
                          <h5 className="truncate font-medium">
                            {getVoiceDisplayName(voice)}
                          </h5>
                          {selectedVoice?.sts_id === voice.sts_id && (
                            <div className="bg-primary h-2 w-2 shrink-0 rounded-full" />
                          )}
                        </div>

                        {getVoiceSubtext(voice) && (
                          <p className="text-muted-foreground mt-1 truncate text-sm">
                            {getVoiceSubtext(voice)}
                          </p>
                        )}

                        {voice.tags?.custom_tags &&
                          voice.tags.custom_tags.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1">
                              {voice.tags.custom_tags
                                .slice(0, 3)
                                .map((tag, index) => (
                                  <Badge
                                    key={index}
                                    variant="outline"
                                    className="px-1.5 py-0 text-xs"
                                  >
                                    {tag}
                                  </Badge>
                                ))}
                              {voice.tags.custom_tags.length > 3 && (
                                <span className="text-muted-foreground text-xs">
                                  +{voice.tags.custom_tags.length - 3}
                                </span>
                              )}
                            </div>
                          )}
                      </div>

                      {/* Play button */}
                      {voice.preview_url && (
                        <div className="opacity-0 transition-all duration-200 group-hover:opacity-100">
                          <PlayPreviewButton
                            voice={voice}
                            providerName={provider}
                            tooltip="Play voice preview"
                          />
                        </div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
