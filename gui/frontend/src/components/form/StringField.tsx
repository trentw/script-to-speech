import React from 'react';

import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import type { ProviderField } from '../../types';

interface StringFieldProps {
  field: ProviderField;
  value: string;
  hasError: boolean;
  onChange: (value: string) => void;
}

export const StringField: React.FC<StringFieldProps> = ({
  field,
  value,
  hasError,
  onChange,
}) => {
  if (field.options && field.options.length > 0) {
    // Dropdown for string fields with options
    return (
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className={hasError ? 'border-destructive' : ''}>
          <SelectValue placeholder={`Select ${field.name}...`} />
        </SelectTrigger>
        <SelectContent>
          {field.options.map((option) => (
            <SelectItem key={option} value={option}>
              {option}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  } else {
    // Text input for regular strings
    return (
      <Input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={field.description || `Enter ${field.name}`}
        className={hasError ? 'border-destructive' : ''}
      />
    );
  }
};
