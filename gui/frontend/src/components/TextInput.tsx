import React from 'react';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

interface TextInputProps {
  value: string;
  onChange: (text: string) => void;
  placeholder?: string;
  label?: string;
  id?: string;
}

export const TextInput: React.FC<TextInputProps> = ({
  value,
  onChange,
  placeholder = "Enter text to convert to speech...",
  label,
  id = "text-input"
}) => {
  return (
    <div className="space-y-2">
      {label && (
        <Label htmlFor={id} className="text-sm font-medium">
          {label}
        </Label>
      )}
      <Textarea
        id={id}
        rows={4}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="resize-none"
      />
      <div className="flex justify-between items-center">
        <span className="text-sm text-muted-foreground">
          {value.length} characters
        </span>
        {value.length > 1000 && (
          <span className="text-sm text-amber-600 dark:text-amber-500">
            Long text may take more time to generate
          </span>
        )}
      </div>
    </div>
  );
};