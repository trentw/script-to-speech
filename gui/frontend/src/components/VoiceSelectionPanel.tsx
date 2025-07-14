import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Search, Play } from 'lucide-react';
import { useCentralAudio } from '../stores/appStore';
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
  onBack
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const { setAudioData } = useCentralAudio();

  const playPreview = (voice: VoiceEntry) => {
    if (!voice?.preview_url) return;
    
    // Load the preview into the central audio player with autoplay
    const voiceName = getVoiceDisplayName(voice);
    setAudioData(
      voice.preview_url,
      `Voice preview: ${voiceName}`,
      `${provider} • ${voiceName}`,
      undefined, // no custom filename for previews
      true // autoplay
    );
  };

  const getVoiceDisplayName = (voice: VoiceEntry) => {
    return voice.description?.provider_name || voice.sts_id;
  };

  const getVoiceSubtext = (voice: VoiceEntry) => {
    const parts = [];
    if (voice.voice_properties?.gender) parts.push(voice.voice_properties.gender);
    if (voice.voice_properties?.accent) parts.push(voice.voice_properties.accent);
    if (voice.description?.perceived_age) parts.push(voice.description.perceived_age);
    return parts.length > 0 ? parts.join(' • ') : voice.description?.custom_description || '';
  };

  const filteredVoices = voices.filter(voice => {
    if (!searchQuery) return true;
    const name = getVoiceDisplayName(voice).toLowerCase();
    const subtext = getVoiceSubtext(voice).toLowerCase();
    const tags = voice.tags?.custom_tags?.join(' ').toLowerCase() || '';
    return name.includes(searchQuery.toLowerCase()) || 
           subtext.includes(searchQuery.toLowerCase()) ||
           tags.includes(searchQuery.toLowerCase());
  });

  return (
    <div className="h-full bg-background flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-border">
        <Button
          variant="ghost"
          size="sm"
          onClick={onBack}
          className="h-8 w-8 p-0"
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h3 className="font-medium">Select a voice</h3>
      </div>

      {/* Search */}
      <div className="p-4 border-b border-border">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search voices..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-border rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          />
        </div>
      </div>

      {/* Voice List */}
      <div className="flex-1 overflow-auto">
        <div className="p-4">
          <div className="space-y-1">
            <h4 className="text-sm font-medium text-muted-foreground mb-3">
              {provider} Voices ({filteredVoices.length})
            </h4>
            
            {filteredVoices.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <p className="text-sm">No voices found</p>
                <p className="text-xs mt-1">Try adjusting your search</p>
              </div>
            ) : (
              <div className="space-y-2">
                {filteredVoices.map((voice) => (
                  <div
                    key={voice.sts_id}
                    className={`group relative rounded-lg border p-3 cursor-pointer transition-all duration-200 ${
                      selectedVoice?.sts_id === voice.sts_id 
                        ? 'border-primary bg-accent text-accent-foreground' 
                        : 'border-border hover:bg-accent hover:text-accent-foreground hover:border-accent'
                    }`}
                    onClick={() => onVoiceSelect(voice)}
                  >
                    <div className="flex items-start gap-3">
                      {/* Voice info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <h5 className="font-medium truncate">
                            {getVoiceDisplayName(voice)}
                          </h5>
                          {selectedVoice?.sts_id === voice.sts_id && (
                            <div className="h-2 w-2 rounded-full bg-primary shrink-0" />
                          )}
                        </div>
                        
                        {getVoiceSubtext(voice) && (
                          <p className="text-sm text-muted-foreground mt-1 truncate">
                            {getVoiceSubtext(voice)}
                          </p>
                        )}

                        {voice.tags?.custom_tags && voice.tags.custom_tags.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {voice.tags.custom_tags.slice(0, 3).map((tag, index) => (
                              <Badge key={index} variant="outline" className="text-xs px-1.5 py-0">
                                {tag}
                              </Badge>
                            ))}
                            {voice.tags.custom_tags.length > 3 && (
                              <span className="text-xs text-muted-foreground">
                                +{voice.tags.custom_tags.length - 3}
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Play button */}
                      {voice.preview_url && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={(e) => {
                            e.stopPropagation();
                            playPreview(voice);
                          }}
                        >
                          <Play className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};