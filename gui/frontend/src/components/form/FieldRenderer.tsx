import React from 'react';
import { StringField } from './StringField';
import { NumberField } from './NumberField';
import { BooleanField } from './BooleanField';
import { JsonField } from './JsonField';
import { Label } from '@/components/ui/label';
import type { ProviderField, ValidationResult } from '../../types';
import { FieldType } from '../../types';

interface FieldRendererProps {
  field: ProviderField;
  value: any;
  validation?: ValidationResult;
  onChange: (fieldName: string, value: any) => void;
}

export const FieldRenderer: React.FC<FieldRendererProps> = ({
  field,
  value,
  validation,
  onChange
}) => {
  const fieldValue = value || '';
  const hasError = validation?.errors.some(error => 
    error.toLowerCase().includes(field.name.toLowerCase())
  ) || false;

  const handleChange = (newValue: any) => {
    onChange(field.name, newValue);
  };

  const renderField = () => {
    switch (field.type) {
      case FieldType.STRING:
        return (
          <StringField
            field={field}
            value={fieldValue}
            hasError={hasError}
            onChange={handleChange}
          />
        );

      case FieldType.INTEGER:
      case FieldType.FLOAT:
        return (
          <NumberField
            field={field}
            value={fieldValue}
            hasError={hasError}
            onChange={handleChange}
          />
        );

      case FieldType.BOOLEAN:
        return (
          <BooleanField
            field={field}
            value={fieldValue}
            onChange={handleChange}
          />
        );

      case FieldType.LIST:
      case FieldType.DICT:
        return (
          <JsonField
            field={field}
            value={fieldValue}
            hasError={hasError}
            onChange={handleChange}
          />
        );

      default:
        // Fallback to string field
        return (
          <StringField
            field={field}
            value={fieldValue}
            hasError={hasError}
            onChange={handleChange}
          />
        );
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium text-foreground">
          {field.name}
          {field.required && <span className="text-destructive ml-1">*</span>}
        </Label>
        {field.default !== undefined && (
          <span className="text-xs text-muted-foreground">
            Default: {typeof field.default === 'string' ? field.default : JSON.stringify(field.default)}
          </span>
        )}
      </div>
      
      {field.description && (
        <p className="text-xs text-muted-foreground">
          {field.description}
        </p>
      )}
      
      {renderField()}
      
      {field.min_value !== undefined && field.max_value !== undefined && (
        <p className="text-xs text-muted-foreground">
          Range: {field.min_value} - {field.max_value}
        </p>
      )}
    </div>
  );
};