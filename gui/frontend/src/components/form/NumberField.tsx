import React from 'react';
import type { ProviderField } from '../../types';
import { FieldType } from '../../types';

interface NumberFieldProps {
  field: ProviderField;
  value: number | string;
  hasError: boolean;
  onChange: (value: number | string) => void;
}

export const NumberField: React.FC<NumberFieldProps> = ({
  field,
  value,
  hasError,
  onChange
}) => {
  const isFloat = field.type === FieldType.FLOAT;
  
  return (
    <input
      type="number"
      step={isFloat ? "0.1" : "1"}
      className={`input-field ${hasError ? 'border-red-500' : ''}`}
      value={value}
      onChange={(e) => {
        const parsedValue = isFloat 
          ? parseFloat(e.target.value) || ''
          : parseInt(e.target.value) || '';
        onChange(parsedValue);
      }}
      min={field.min_value}
      max={field.max_value}
      placeholder={field.description || `Enter ${field.name}`}
    />
  );
};