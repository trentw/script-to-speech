import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

interface VoiceTextEditorProps {
  name: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
}

export function VoiceTextEditor({
  name,
  label,
  value,
  onChange,
  placeholder,
  rows = 2,
}: VoiceTextEditorProps) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={name} className="text-xs font-medium">
        {label}
      </Label>
      <Textarea
        id={name}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        className="resize-none text-xs"
      />
    </div>
  );
}
