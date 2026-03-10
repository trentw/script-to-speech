import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import type { SchemaPropertyDefinition } from '../../types/voice-editor';

interface VoiceEnumSelectorProps {
  name: string;
  schema: SchemaPropertyDefinition;
  value: string | undefined;
  onChange: (value: string) => void;
}

export function VoiceEnumSelector({
  name,
  schema,
  value,
  onChange,
}: VoiceEnumSelectorProps) {
  const values = schema.values ?? [];

  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-medium capitalize">{name}</Label>
      <Select value={value ?? ''} onValueChange={onChange}>
        <SelectTrigger className="h-8 w-full text-xs">
          <SelectValue placeholder={`Select ${name}...`} />
        </SelectTrigger>
        <SelectContent>
          {values.map((v) => (
            <SelectItem key={v} value={v} className="text-xs">
              {v.replace(/_/g, ' ')}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
