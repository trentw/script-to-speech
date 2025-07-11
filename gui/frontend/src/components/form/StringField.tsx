import React from 'react';
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
  onChange
}) => {
  if (field.options && field.options.length > 0) {
    // Dropdown for string fields with options
    return (
      <select
        className={`select-field ${hasError ? 'border-red-500' : ''}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Select {field.name}...</option>
        {field.options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  } else {
    // Text input for regular strings
    return (
      <input
        type="text"
        className={`input-field ${hasError ? 'border-red-500' : ''}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={field.description || `Enter ${field.name}`}
      />
    );
  }
};