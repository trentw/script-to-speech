import React, { useState, useEffect } from 'react';
import { FieldRenderer } from './form/FieldRenderer';
import type { ProviderInfo, ValidationResult } from '../types';
import { apiService } from '../services/api';

interface ConfigFormProps {
  provider: string;
  providerInfo?: ProviderInfo;
  config: Record<string, any>;
  onConfigChange: (config: Record<string, any>) => void;
}

export const ConfigForm: React.FC<ConfigFormProps> = ({
  provider,
  providerInfo,
  config,
  onConfigChange
}) => {
  const [validation, setValidation] = useState<ValidationResult | undefined>(undefined);
  const [isValidating, setIsValidating] = useState(false);

  // Validate configuration when it changes
  useEffect(() => {
    const validateConfig = async () => {
      if (!provider || Object.keys(config).length === 0) {
        setValidation(undefined);
        return;
      }

      setIsValidating(true);
      const response = await apiService.validateProviderConfig(provider, config);
      setIsValidating(false);

      if (response.data) {
        setValidation(response.data);
      } else {
        setValidation({
          valid: false,
          errors: [response.error || 'Validation failed'],
          warnings: []
        });
      }
    };

    const debounceTimeout = setTimeout(validateConfig, 500);
    return () => clearTimeout(debounceTimeout);
  }, [provider, config]);

  const updateField = (fieldName: string, value: any) => {
    const newConfig = { ...config };
    
    if (value === '' || value === null || value === undefined) {
      delete newConfig[fieldName];
    } else {
      newConfig[fieldName] = value;
    }
    
    onConfigChange(newConfig);
  };

  const handleFieldChange = (fieldName: string, value: any) => {
    updateField(fieldName, value);
  };

  if (!providerInfo) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p>Loading provider configuration...</p>
      </div>
    );
  }

  const hasRequiredFields = providerInfo.required_fields.length > 0;
  const hasOptionalFields = providerInfo.optional_fields.length > 0;

  return (
    <div className="space-y-6">
      {/* Voice Library Configuration Banner */}
      {config.sts_id && (
        <div className="px-3 py-2 bg-primary/5 border border-primary/20 rounded-lg">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary" />
            <span className="text-sm font-medium text-foreground">Voice: {config.sts_id}</span>
          </div>
          <p className="text-xs text-muted-foreground mt-1 pl-4">
            Parameters populated from voice library
          </p>
        </div>
      )}

      {/* All Fields - Combined with better organization */}
      {(hasRequiredFields || hasOptionalFields) && (
        <div className="space-y-4">
          {/* Required fields first */}
          {providerInfo.required_fields.map((field) => (
            <div key={field.name} className="space-y-2">
              <FieldRenderer
                field={field}
                value={config[field.name]}
                validation={validation}
                onChange={handleFieldChange}
              />
            </div>
          ))}
          
          {/* Optional fields after */}
          {providerInfo.optional_fields.map((field) => (
            <div key={field.name} className="space-y-2">
              <FieldRenderer
                field={field}
                value={config[field.name]}
                validation={validation}
                onChange={handleFieldChange}
              />
            </div>
          ))}
        </div>
      )}

      {/* No fields message */}
      {!hasRequiredFields && !hasOptionalFields && (
        <div className="text-center py-8 text-muted-foreground">
          <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center mx-auto mb-3">
            <span className="text-lg">⚙️</span>
          </div>
          <p className="text-sm">No additional settings</p>
          <p className="text-xs mt-1 opacity-75">This provider is ready to use</p>
        </div>
      )}

      {/* Compact Status Indicator */}
      {(validation || isValidating) && (
        <div className="flex items-center justify-between pt-3 border-t border-border">
          <div className="flex items-center gap-2">
            {isValidating ? (
              <>
                <div className="w-3 h-3 border border-primary border-t-transparent rounded-full animate-spin" />
                <span className="text-xs text-muted-foreground">Validating...</span>
              </>
            ) : validation?.valid ? (
              <>
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span className="text-xs text-green-600 dark:text-green-400">Valid configuration</span>
              </>
            ) : (
              <>
                <div className="w-3 h-3 rounded-full bg-destructive" />
                <span className="text-xs text-destructive">
                  {validation?.errors.length || 0} error{validation?.errors.length !== 1 ? 's' : ''}
                </span>
              </>
            )}
          </div>
          
          {validation?.warnings && validation.warnings.length > 0 && (
            <span className="text-xs text-amber-600 dark:text-amber-400">
              {validation.warnings.length} warning{validation.warnings.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      )}

      {/* Detailed error display when needed */}
      {validation && !validation.valid && validation.errors.length > 0 && (
        <div className="p-3 bg-destructive/5 border border-destructive/20 rounded-lg">
          <div className="space-y-1">
            {validation.errors.map((error, index) => (
              <p key={index} className="text-xs text-destructive">• {error}</p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};