import React, { useState } from 'react';

import { Input } from '@/components/ui/input';
import { Slider } from '@/components/ui/slider';

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
  onChange,
}) => {
  const isFloat = field.type === FieldType.FLOAT;
  const [inputFocused, setInputFocused] = useState(false);

  // Convert value to number for calculations
  const numericValue =
    typeof value === 'number' ? value : parseFloat(String(value)) || 0;

  // Determine if we should show a slider (when we have min/max range)
  const hasRange =
    field.min_value !== undefined && field.max_value !== undefined;
  const showSlider =
    hasRange &&
    field.min_value !== undefined &&
    field.max_value !== undefined &&
    field.max_value - field.min_value <= 100; // Only for reasonable ranges

  const handleSliderChange = (values: number[]) => {
    const newValue = values[0];
    const finalValue = isFloat ? newValue : Math.round(newValue);
    onChange(finalValue);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value;
    if (inputValue === '') {
      onChange('');
      return;
    }

    const parsedValue = isFloat ? parseFloat(inputValue) : parseInt(inputValue);

    if (!isNaN(parsedValue)) {
      onChange(parsedValue);
    }
  };

  // Format display value
  const displayValue =
    typeof value === 'number'
      ? isFloat
        ? value.toFixed(2).replace(/\.?0+$/, '')
        : value.toString()
      : String(value || '');

  if (showSlider) {
    return (
      <div className="space-y-4">
        {/* Slider with ElevenLabs-style labels */}
        <div className="space-y-3">
          <div className="text-muted-foreground flex items-center justify-between text-xs">
            <span>{field.min_value}</span>
            <span>{field.max_value}</span>
          </div>

          <Slider
            value={[numericValue || field.default || field.min_value]}
            onValueChange={handleSliderChange}
            min={field.min_value}
            max={field.max_value}
            step={isFloat ? 0.01 : 1}
            className="w-full"
          />

          {/* Current value display */}
          <div className="text-center">
            <span className="text-foreground text-sm font-medium">
              {displayValue || field.default || field.min_value}
            </span>
          </div>
        </div>

        {/* Optional precise input - smaller and less prominent */}
        {inputFocused && (
          <Input
            type="number"
            step={isFloat ? '0.01' : '1'}
            value={displayValue}
            onChange={handleInputChange}
            onBlur={() => setInputFocused(false)}
            min={field.min_value}
            max={field.max_value}
            placeholder="Enter precise value"
            className={`text-sm ${hasError ? 'border-destructive' : ''}`}
          />
        )}

        {!inputFocused && (
          <button
            type="button"
            onClick={() => setInputFocused(true)}
            className="text-muted-foreground hover:text-foreground text-xs transition-colors"
          >
            Enter precise value
          </button>
        )}
      </div>
    );
  }

  // Fallback to regular input for unbounded ranges
  return (
    <Input
      type="number"
      step={isFloat ? '0.01' : '1'}
      value={displayValue}
      onChange={handleInputChange}
      min={field.min_value}
      max={field.max_value}
      placeholder={field.description || `Enter ${field.name}`}
      className={hasError ? 'border-destructive' : ''}
    />
  );
};
