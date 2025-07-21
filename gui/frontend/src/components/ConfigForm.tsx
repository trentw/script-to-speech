import React, { useEffect, useState } from 'react';

import { apiService } from '../services/api';
import type { ProviderInfo, ValidationResult } from '../types';
import { FieldRenderer } from './form/FieldRenderer';

// Import Config type from appStore
type ConfigValue = string | number | boolean | string[];
type Config = Record<string, ConfigValue>;

interface ConfigFormProps {
  provider: string;
  providerInfo?: ProviderInfo;
  config: Config;
  onConfigChange: (config: Config) => void;
}

export const ConfigForm: React.FC<ConfigFormProps> = ({
  provider,
  providerInfo,
  config,
  onConfigChange,
}) => {
  const [validation, setValidation] = useState<ValidationResult | undefined>(
    undefined
  );
  const [isValidating, setIsValidating] = useState(false);

  // Validate configuration when it changes
  useEffect(() => {
    const validateConfig = async () => {
      if (!provider || Object.keys(config).length === 0) {
        setValidation(undefined);
        return;
      }

      setIsValidating(true);
      const response = await apiService.validateProviderConfig(
        provider,
        config
      );
      setIsValidating(false);

      if (response.data) {
        setValidation(response.data);
      } else {
        setValidation({
          valid: false,
          errors: [response.error || 'Validation failed'],
          warnings: [],
        });
      }
    };

    const debounceTimeout = setTimeout(validateConfig, 500);
    return () => clearTimeout(debounceTimeout);
  }, [provider, config]);

  const updateField = (fieldName: string, value: ConfigValue) => {
    const newConfig = { ...config };

    if (value === '' || value === null || value === undefined) {
      delete newConfig[fieldName];
    } else {
      newConfig[fieldName] = value;
    }

    onConfigChange(newConfig);
  };

  const handleFieldChange = (fieldName: string, value: ConfigValue) => {
    updateField(fieldName, value);
  };

  if (!providerInfo) {
    return (
      <div className="text-muted-foreground py-8 text-center">
        <p>Loading provider configuration...</p>
      </div>
    );
  }

  const hasRequiredFields = providerInfo.required_fields.length > 0;
  const hasOptionalFields = providerInfo.optional_fields.length > 0;

  const resetToDefaults = () => {
    const defaultConfig: Config = {};

    // Preserve sts_id if it exists
    if (config.sts_id) {
      defaultConfig.sts_id = config.sts_id;
    }

    // Set default values for all fields
    [
      ...(providerInfo?.required_fields || []),
      ...(providerInfo?.optional_fields || []),
    ].forEach((field) => {
      if (field.default !== undefined) {
        defaultConfig[field.name] = field.default;
      }
    });

    onConfigChange(defaultConfig);
  };

  return (
    <div className="space-y-6">
      {/* Voice Library Configuration Banner */}
      {config.sts_id && (
        <div className="bg-primary/5 border-primary/20 rounded-lg border px-3 py-2">
          <div className="flex items-center gap-2">
            <div className="bg-primary h-2 w-2 rounded-full" />
            <span className="text-foreground text-sm font-medium">
              Voice: {config.sts_id}
            </span>
          </div>
          <p className="text-muted-foreground mt-1 pl-4 text-xs">
            Parameters populated from voice library
          </p>
        </div>
      )}

      {/* Fields - Organized by requirement level */}
      {(hasRequiredFields || hasOptionalFields) && (
        <div className="space-y-6">
          {/* Required fields section */}
          {hasRequiredFields && (
            <div className="space-y-4">
              {hasOptionalFields && (
                <div className="text-muted-foreground text-xs font-medium tracking-wider uppercase">
                  Required Settings
                </div>
              )}
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
            </div>
          )}

          {/* Optional fields section */}
          {hasOptionalFields && (
            <div className="space-y-4">
              {hasRequiredFields && (
                <div className="text-muted-foreground border-border border-t pt-4 text-xs font-medium tracking-wider uppercase">
                  Optional Settings
                </div>
              )}
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
        </div>
      )}

      {/* No fields message */}
      {!hasRequiredFields && !hasOptionalFields && (
        <div className="text-muted-foreground py-8 text-center">
          <div className="bg-muted mx-auto mb-3 flex h-8 w-8 items-center justify-center rounded-full">
            <span className="text-lg">⚙️</span>
          </div>
          <p className="text-sm">No additional settings</p>
          <p className="mt-1 text-xs opacity-75">
            This provider is ready to use
          </p>
        </div>
      )}

      {/* Compact Status Indicator */}
      {(validation || isValidating) && (
        <div className="border-border flex items-center justify-between border-t pt-3">
          <div className="flex items-center gap-2">
            {isValidating ? (
              <>
                <div className="border-primary h-3 w-3 animate-spin rounded-full border border-t-transparent" />
                <span className="text-muted-foreground text-xs">
                  Validating...
                </span>
              </>
            ) : validation?.valid ? (
              <>
                <div className="h-3 w-3 rounded-full bg-green-500" />
                <span className="text-xs text-green-600">
                  Valid configuration
                </span>
              </>
            ) : (
              <>
                <div className="bg-destructive h-3 w-3 rounded-full" />
                <span className="text-destructive text-xs">
                  {validation?.errors.length || 0} error
                  {validation?.errors.length !== 1 ? 's' : ''}
                </span>
              </>
            )}
          </div>

          {validation?.warnings && validation.warnings.length > 0 && (
            <span className="text-xs text-amber-600">
              {validation.warnings.length} warning
              {validation.warnings.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      )}

      {/* Detailed error display when needed */}
      {validation && !validation.valid && validation.errors.length > 0 && (
        <div className="bg-destructive/5 border-destructive/20 rounded-lg border p-3">
          <div className="space-y-1">
            {validation.errors.map((error, index) => (
              <p key={index} className="text-destructive text-xs">
                • {error}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Reset button - ElevenLabs style */}
      {(hasRequiredFields || hasOptionalFields) && (
        <div className="border-border border-t pt-4">
          <button
            type="button"
            onClick={resetToDefaults}
            className="text-muted-foreground hover:text-foreground flex items-center gap-2 text-sm transition-colors"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Reset values
          </button>
        </div>
      )}
    </div>
  );
};
