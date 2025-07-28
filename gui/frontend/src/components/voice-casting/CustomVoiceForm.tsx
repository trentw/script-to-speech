import { Loader2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { useProviderMetadata } from '@/hooks/queries/useProviderMetadata';
import { FieldType, type ProviderField } from '@/types';

interface CustomVoiceFormProps {
  provider: string;
  currentConfig?: Record<string, unknown>;
  onConfigChange: (config: Record<string, unknown>) => void;
  onCancel: () => void;
}

export function CustomVoiceForm({
  provider,
  currentConfig = {},
  onConfigChange,
  onCancel,
}: CustomVoiceFormProps) {
  const {
    data: providerInfo,
    isLoading,
    error,
  } = useProviderMetadata(provider);
  const [formValues, setFormValues] = useState<Record<string, unknown>>(() => ({
    ...currentConfig,
  }));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const hasInitialized = useRef(false);

  // Initialize form values when provider info loads
  useEffect(() => {
    if (providerInfo && !hasInitialized.current) {
      hasInitialized.current = true;
      const initialValues: Record<string, unknown> = { ...currentConfig };

      // Set defaults for required fields if not present
      providerInfo.required_fields.forEach((field) => {
        if (!(field.name in initialValues) && field.default !== undefined) {
          initialValues[field.name] = field.default;
        }
      });

      setFormValues(initialValues);
    }
  }, [providerInfo, currentConfig]);

  const handleFieldChange = (fieldName: string, value: unknown) => {
    setFormValues((prev) => ({
      ...prev,
      [fieldName]: value,
    }));

    // Clear error for this field
    setErrors((prev) => {
      const newErrors = { ...prev };
      delete newErrors[fieldName];
      return newErrors;
    });
  };

  const validateForm = (): boolean => {
    if (!providerInfo) return false;

    const newErrors: Record<string, string> = {};

    // Validate required fields
    providerInfo.required_fields.forEach((field) => {
      const value = formValues[field.name];

      if (value === undefined || value === null || value === '') {
        newErrors[field.name] = 'This field is required';
      } else {
        // Type-specific validation
        const error = validateFieldValue(field, value);
        if (error) {
          newErrors[field.name] = error;
        }
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateFieldValue = (
    field: ProviderField,
    value: unknown
  ): string | null => {
    // Type validation
    switch (field.type) {
      case FieldType.STRING:
        if (typeof value !== 'string') {
          return 'Must be a string';
        }
        if (field.options && !field.options.includes(value)) {
          return `Must be one of: ${field.options.join(', ')}`;
        }
        break;
      case FieldType.INTEGER:
        if (!Number.isInteger(Number(value))) {
          return 'Must be an integer';
        }
        break;
      case FieldType.FLOAT:
        if (isNaN(Number(value))) {
          return 'Must be a number';
        }
        break;
      case FieldType.BOOLEAN:
        if (typeof value !== 'boolean') {
          return 'Must be true or false';
        }
        break;
    }

    // Range validation for numeric types
    if (field.type === FieldType.INTEGER || field.type === FieldType.FLOAT) {
      const numValue = Number(value);
      if (field.min_value !== undefined && numValue < field.min_value) {
        return `Must be at least ${field.min_value}`;
      }
      if (field.max_value !== undefined && numValue > field.max_value) {
        return `Must be at most ${field.max_value}`;
      }
    }

    return null;
  };

  const handleSubmit = () => {
    if (validateForm()) {
      onConfigChange(formValues);
    }
  };

  const renderField = (field: ProviderField) => {
    const value = formValues[field.name] ?? field.default ?? '';
    const error = errors[field.name];

    switch (field.type) {
      case FieldType.STRING:
        if (field.options) {
          return (
            <div key={field.name} className="space-y-2">
              <Label htmlFor={field.name}>
                {field.name
                  .replace(/_/g, ' ')
                  .replace(/\b\w/g, (l) => l.toUpperCase())}
                {field.required && (
                  <span className="text-destructive ml-1">*</span>
                )}
              </Label>
              <Select
                value={value as string}
                onValueChange={(val) => handleFieldChange(field.name, val)}
              >
                <SelectTrigger
                  id={field.name}
                  className={error ? 'border-destructive' : ''}
                >
                  <SelectValue placeholder={`Select ${field.name}`} />
                </SelectTrigger>
                <SelectContent>
                  {field.options.map((option) => (
                    <SelectItem key={option} value={option}>
                      {option}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {field.description && (
                <p className="text-muted-foreground text-sm">
                  {field.description}
                </p>
              )}
              {error && <p className="text-destructive text-sm">{error}</p>}
            </div>
          );
        }
        return (
          <div key={field.name} className="space-y-2">
            <Label htmlFor={field.name}>
              {field.name
                .replace(/_/g, ' ')
                .replace(/\b\w/g, (l) => l.toUpperCase())}
              {field.required && (
                <span className="text-destructive ml-1">*</span>
              )}
            </Label>
            <Input
              id={field.name}
              type="text"
              value={value as string}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              className={error ? 'border-destructive' : ''}
              placeholder={field.description}
            />
            {field.description && !error && (
              <p className="text-muted-foreground text-sm">
                {field.description}
              </p>
            )}
            {error && <p className="text-destructive text-sm">{error}</p>}
          </div>
        );

      case FieldType.INTEGER:
      case FieldType.FLOAT:
        return (
          <div key={field.name} className="space-y-2">
            <Label htmlFor={field.name}>
              {field.name
                .replace(/_/g, ' ')
                .replace(/\b\w/g, (l) => l.toUpperCase())}
              {field.required && (
                <span className="text-destructive ml-1">*</span>
              )}
            </Label>
            <Input
              id={field.name}
              type="number"
              value={value as number}
              onChange={(e) => {
                const val =
                  field.type === FieldType.INTEGER
                    ? parseInt(e.target.value, 10)
                    : parseFloat(e.target.value);
                handleFieldChange(field.name, isNaN(val) ? '' : val);
              }}
              step={field.type === FieldType.FLOAT ? 'any' : '1'}
              min={field.min_value}
              max={field.max_value}
              className={error ? 'border-destructive' : ''}
              placeholder={field.description}
            />
            {field.description && !error && (
              <p className="text-muted-foreground text-sm">
                {field.description}
                {(field.min_value !== undefined ||
                  field.max_value !== undefined) && (
                  <span className="block">
                    Range: {field.min_value ?? '-∞'} to {field.max_value ?? '∞'}
                  </span>
                )}
              </p>
            )}
            {error && <p className="text-destructive text-sm">{error}</p>}
          </div>
        );

      case FieldType.BOOLEAN:
        return (
          <div key={field.name} className="flex items-center space-x-2">
            <Switch
              id={field.name}
              checked={value as boolean}
              onCheckedChange={(checked) =>
                handleFieldChange(field.name, checked)
              }
            />
            <Label htmlFor={field.name} className="flex-1">
              {field.name
                .replace(/_/g, ' ')
                .replace(/\b\w/g, (l) => l.toUpperCase())}
              {field.required && (
                <span className="text-destructive ml-1">*</span>
              )}
              {field.description && (
                <span className="text-muted-foreground block text-sm font-normal">
                  {field.description}
                </span>
              )}
            </Label>
          </div>
        );

      default:
        return null;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center">
        <p className="text-destructive">
          Failed to load provider configuration
        </p>
        <p className="text-muted-foreground text-sm">{error.message}</p>
      </div>
    );
  }

  if (!providerInfo) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold">
          Custom {providerInfo.name} Voice Configuration
        </h3>
        <p className="text-muted-foreground text-sm">
          Configure the required fields for your custom voice
        </p>
      </div>

      <div className="space-y-4">
        {/* Required fields */}
        {providerInfo.required_fields.length > 0 && (
          <>
            <h4 className="text-muted-foreground text-sm font-medium">
              Required Fields
            </h4>
            {providerInfo.required_fields.map(renderField)}
          </>
        )}

        {/* Optional fields - for future enhancement */}
        {/* {providerInfo.optional_fields.length > 0 && (
          <>
            <h4 className="text-sm font-medium text-muted-foreground mt-6">Optional Fields</h4>
            {providerInfo.optional_fields.map(renderField)}
          </>
        )} */}
      </div>

      <div className="flex justify-end space-x-2">
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={handleSubmit}>Apply Configuration</Button>
      </div>
    </div>
  );
}
