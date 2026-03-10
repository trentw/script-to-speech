import { X } from 'lucide-react';
import { useCallback, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface VoiceTagEditorProps {
  label: string;
  tags: string[];
  onChange: (tags: string[]) => void;
}

function sanitizeTag(raw: string): string {
  return raw
    .toLowerCase()
    .replace(/\s+/g, '_')
    .replace(/[^a-z0-9_-]/g, '');
}

export function VoiceTagEditor({ label, tags, onChange }: VoiceTagEditorProps) {
  const [inputValue, setInputValue] = useState('');

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && inputValue.trim()) {
        e.preventDefault();
        const newTag = sanitizeTag(inputValue);
        if (newTag && !tags.includes(newTag)) {
          onChange([...tags, newTag]);
        }
        setInputValue('');
      }
    },
    [inputValue, tags, onChange]
  );

  const handleRemove = useCallback(
    (tag: string) => {
      onChange(tags.filter((t) => t !== tag));
    },
    [tags, onChange]
  );

  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-medium">{label}</Label>
      <div className="flex min-h-[28px] flex-wrap gap-1.5">
        {tags.map((tag) => (
          <Badge
            key={tag}
            variant="secondary"
            className="gap-1 pr-1 text-xs select-none"
          >
            {tag}
            <button
              type="button"
              onClick={() => handleRemove(tag)}
              className="hover:bg-destructive/20 hover:text-destructive ml-0.5 cursor-pointer rounded-full p-0.5 transition-colors"
              aria-label={`Remove ${tag}`}
            >
              <X className="size-3" />
            </button>
          </Badge>
        ))}
      </div>
      <Input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type and press Enter to add..."
        className="h-7 text-xs"
      />
    </div>
  );
}
