import React from 'react';
import type { ProviderField } from '../../types';
import { FieldType } from '../../types';

interface JsonFieldProps {
  field: ProviderField;
  value: any;
  hasError: boolean;
  onChange: (value: any) => void;
}

export const JsonField: React.FC<JsonFieldProps> = ({
  field,
  value,
  hasError,
  onChange
}) => {
  const isList = field.type === FieldType.LIST;
  const rows = isList ? 3 : 4;
  const placeholder = isList 
    ? `Enter ${field.name} as JSON array`
    : `Enter ${field.name} as JSON object`;
  const exampleText = isList 
    ? 'Enter as JSON array, e.g., ["item1", "item2"]'
    : 'Enter as JSON object, e.g., {"key": "value"}';

  const displayValue = () => {
    if (isList && Array.isArray(value)) {
      return JSON.stringify(value, null, 2);
    } else if (!isList && typeof value === 'object' && value !== null) {
      return JSON.stringify(value, null, 2);
    }
    return value || '';
  };

  const handleChange = (inputValue: string) => {
    try {
      const parsed = JSON.parse(inputValue);
      onChange(parsed);
    } catch {
      // Keep as string until valid JSON
      onChange(inputValue);
    }
  };

  return (
    <div>
      <textarea
        className={`input-field ${hasError ? 'border-red-500' : ''}`}
        rows={rows}
        value={displayValue()}
        onChange={(e) => handleChange(e.target.value)}
        placeholder={field.description || placeholder}
      />
      <p className="text-xs text-gray-500 mt-1">
        {exampleText}
      </p>
    </div>
  );
};