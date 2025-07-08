import React, { useState } from 'react';
import type { VoiceEntry } from '../types';

interface VoiceSelectorProps {
  provider: string;
  voices: VoiceEntry[];
  selectedVoice?: VoiceEntry;
  onVoiceSelect: (voice: VoiceEntry) => void;
}

export const VoiceSelector: React.FC<VoiceSelectorProps> = ({
  provider,
  voices,
  selectedVoice,
  onVoiceSelect
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');

  // Filter voices based on search query
  const filteredVoices = voices.filter(voice => {
    const searchLower = searchQuery.toLowerCase();
    return (
      voice.sts_id.toLowerCase().includes(searchLower) ||
      voice.description?.provider_name?.toLowerCase().includes(searchLower) ||
      voice.description?.custom_description?.toLowerCase().includes(searchLower) ||
      voice.tags?.custom_tags?.some(tag => tag.toLowerCase().includes(searchLower))
    );
  });

  const playPreview = (voice: VoiceEntry) => {
    if (voice.preview_url) {
      const audio = new Audio(voice.preview_url);
      audio.play().catch(console.error);
    }
  };

  const VoiceCard: React.FC<{ voice: VoiceEntry }> = ({ voice }) => (
    <div
      className={`p-4 border rounded-lg cursor-pointer transition-all ${
        selectedVoice?.sts_id === voice.sts_id
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
      }`}
      onClick={() => onVoiceSelect(voice)}
    >
      <div className="flex justify-between items-start mb-2">
        <div>
          <h4 className="font-medium text-gray-900">{voice.sts_id}</h4>
          {voice.description?.provider_name && (
            <p className="text-sm text-gray-600">{voice.description.provider_name}</p>
          )}
        </div>
        {voice.preview_url && (
          <button
            className="text-blue-600 hover:text-blue-800 text-sm"
            onClick={(e) => {
              e.stopPropagation();
              playPreview(voice);
            }}
          >
            ▶️ Preview
          </button>
        )}
      </div>

      {voice.description?.custom_description && (
        <p className="text-sm text-gray-700 mb-2">
          {voice.description.custom_description}
        </p>
      )}

      {voice.voice_properties && (
        <div className="flex flex-wrap gap-2 mb-2">
          {voice.voice_properties.gender && (
            <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
              {voice.voice_properties.gender}
            </span>
          )}
          {voice.voice_properties.accent && (
            <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
              {voice.voice_properties.accent}
            </span>
          )}
          {voice.description?.perceived_age && (
            <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
              {voice.description.perceived_age}
            </span>
          )}
        </div>
      )}

      {voice.tags?.custom_tags && voice.tags.custom_tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {voice.tags.custom_tags.slice(0, 3).map((tag, index) => (
            <span
              key={index}
              className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded"
            >
              {tag}
            </span>
          ))}
          {voice.tags.custom_tags.length > 3 && (
            <span className="text-xs text-gray-500">
              +{voice.tags.custom_tags.length - 3} more
            </span>
          )}
        </div>
      )}
    </div>
  );

  if (voices.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No voices available for {provider}</p>
        <p className="text-sm mt-1">
          You can still configure the provider manually below
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* Search and view controls */}
      <div className="flex gap-4 mb-4">
        <div className="flex-1">
          <input
            type="text"
            className="input-field"
            placeholder="Search voices..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="flex border border-gray-300 rounded-md">
          <button
            className={`px-3 py-2 text-sm ${
              viewMode === 'list'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
            onClick={() => setViewMode('list')}
          >
            List
          </button>
          <button
            className={`px-3 py-2 text-sm border-l border-gray-300 ${
              viewMode === 'grid'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
            onClick={() => setViewMode('grid')}
          >
            Grid
          </button>
        </div>
      </div>

      {/* Results count */}
      <div className="mb-4 text-sm text-gray-600">
        {filteredVoices.length} of {voices.length} voices
        {searchQuery && ` matching "${searchQuery}"`}
      </div>

      {/* Voice selection option */}
      <div className="mb-4 p-3 border border-dashed border-gray-300 rounded-lg">
        <button
          className={`w-full text-left p-2 rounded ${
            !selectedVoice
              ? 'bg-blue-50 border border-blue-200'
              : 'hover:bg-gray-50'
          }`}
          onClick={() => onVoiceSelect({ 
            sts_id: '', 
            provider, 
            config: {} 
          } as VoiceEntry)}
        >
          <div className="font-medium text-gray-900">Manual Configuration</div>
          <div className="text-sm text-gray-600">
            Configure provider settings manually without using voice library
          </div>
        </button>
      </div>

      {/* Voice list/grid */}
      {filteredVoices.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No voices match your search</p>
        </div>
      ) : (
        <div
          className={
            viewMode === 'grid'
              ? 'grid grid-cols-1 md:grid-cols-2 gap-4'
              : 'space-y-3'
          }
        >
          {filteredVoices.map((voice) => (
            <VoiceCard key={voice.sts_id} voice={voice} />
          ))}
        </div>
      )}
    </div>
  );
};