import React, { useState } from 'react';
import { Slider } from '@/components/ui/slider';
import { Input } from '@/components/ui/input';
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
  const [inputFocused, setInputFocused] = useState(false);
  
  // Convert value to number for calculations
  const numericValue = typeof value === 'number' ? value : (parseFloat(String(value)) || 0);
  
  // Determine if we should show a slider (when we have min/max range)
  const hasRange = field.min_value !== undefined && field.max_value !== undefined;
  const showSlider = hasRange && (field.max_value - field.min_value) <= 100; // Only for reasonable ranges
  
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
    
    const parsedValue = isFloat 
      ? parseFloat(inputValue)
      : parseInt(inputValue);
    
    if (!isNaN(parsedValue)) {
      onChange(parsedValue);
    }
  };
  
  // Format display value
  const displayValue = typeof value === 'number' 
    ? (isFloat ? value.toFixed(2).replace(/\.?0+$/, '') : value.toString())
    : String(value || '');

  if (showSlider) {
    return (
      <div className="space-y-3">
        {/* Slider with refined value display */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground font-mono">
              {field.min_value}
            </span>
            <div className="px-2.5 py-1 bg-accent/50 rounded-md text-sm font-medium min-w-[50px] text-center border">
              {displayValue || field.default || field.min_value}
            </div>
            <span className="text-xs text-muted-foreground font-mono">
              {field.max_value}
            </span>
          </div>
          
          <Slider
            value={[numericValue || field.default || field.min_value]}
            onValueChange={handleSliderChange}
            min={field.min_value}
            max={field.max_value}
            step={isFloat ? 0.01 : 1}
            className="w-full"
          />
        </div>
        
        {/* Compact precise input */}
        <Input
          type="number"
          step={isFloat ? "0.01" : "1"}
          value={displayValue}
          onChange={handleInputChange}
          onFocus={() => setInputFocused(true)}
          onBlur={() => setInputFocused(false)}
          min={field.min_value}
          max={field.max_value}
          placeholder="Or enter precise value"
          className={`text-sm ${hasError ? 'border-destructive' : ''} ${
            inputFocused ? 'ring-2 ring-primary/20' : ''
          }`}
        />
      </div>
    );
  }

  // Fallback to regular input for unbounded ranges
  return (
    <Input
      type="number"
      step={isFloat ? "0.01" : "1"}
      value={displayValue}
      onChange={handleInputChange}
      min={field.min_value}
      max={field.max_value}
      placeholder={field.description || `Enter ${field.name}`}
      className={hasError ? 'border-destructive' : ''}
    />
  );
};