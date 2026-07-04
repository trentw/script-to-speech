import { Plus, Trash2 } from 'lucide-react';
import React, { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

import { StringListField } from './StringListField';

interface SpeakerMapFieldProps {
  value: Record<string, string[]>;
  onChange: (value: Record<string, string[]>) => void;
}

/**
 * Editor for dict-of-string-lists configs (speaker_merge): a canonical
 * speaker name mapping to the variations merged into it.
 */
export const SpeakerMapField: React.FC<SpeakerMapFieldProps> = ({
  value,
  onChange,
}) => {
  const [newSpeaker, setNewSpeaker] = useState('');

  const addSpeaker = () => {
    const trimmed = newSpeaker.trim();
    if (!trimmed || trimmed in value) {
      setNewSpeaker('');
      return;
    }
    onChange({ ...value, [trimmed]: [] });
    setNewSpeaker('');
  };

  const removeSpeaker = (speaker: string) => {
    const next = { ...value };
    delete next[speaker];
    onChange(next);
  };

  return (
    <div className="space-y-3">
      {Object.entries(value).map(([speaker, variants]) => (
        <div key={speaker} className="rounded-md border p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="font-mono text-sm font-semibold">{speaker}</span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-label={`Remove ${speaker}`}
              onClick={() => removeSpeaker(speaker)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
          <Label className="text-muted-foreground mb-1 block text-xs">
            Variations merged into {speaker}
          </Label>
          <StringListField
            value={variants}
            onChange={(next) => onChange({ ...value, [speaker]: next })}
            placeholder="e.g. BOB O.S."
          />
        </div>
      ))}
      <div className="flex gap-2">
        <Input
          value={newSpeaker}
          placeholder="Canonical speaker name (e.g. BOB)"
          className="h-8 text-sm"
          onChange={(e) => setNewSpeaker(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              addSpeaker();
            }
          }}
        />
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={addSpeaker}
          disabled={!newSpeaker.trim()}
        >
          <Plus className="mr-1 h-4 w-4" />
          Speaker
        </Button>
      </div>
    </div>
  );
};
