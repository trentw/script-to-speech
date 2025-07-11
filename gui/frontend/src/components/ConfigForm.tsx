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
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  // Validate configuration when it changes
  useEffect(() => {
    const validateConfig = async () => {
      if (!provider || Object.keys(config).length === 0) {
        setValidation(null);
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
      <div className="text-center py-8 text-gray-500">
        <p>Loading provider configuration...</p>
      </div>
    );
  }

  const hasRequiredFields = providerInfo.required_fields.length > 0;
  const hasOptionalFields = providerInfo.optional_fields.length > 0;

  return (
    <div className="space-y-6">
      {/* STS ID field (special case) */}
      {config.sts_id && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-md">
          <div className="flex items-center">
            <span className="text-green-800 font-medium">Voice Library ID:</span>
            <span className="ml-2 text-green-700">{config.sts_id}</span>
          </div>
          <p className="text-sm text-green-600 mt-1">
            Configuration populated from voice library. You can override any field below.
          </p>
        </div>
      )}

      {/* Required Fields */}
      {hasRequiredFields && (
        <div>
          <h3 className="text-md font-medium text-gray-900 mb-3">
            Required Fields
          </h3>
          <div className="space-y-4">
            {providerInfo.required_fields.map((field) => (
              <FieldRenderer
                key={field.name}
                field={field}
                value={config[field.name]}
                validation={validation}
                onChange={handleFieldChange}
              />
            ))}
          </div>
        </div>
      )}

      {/* Optional Fields */}
      {hasOptionalFields && (
        <div>
          <h3 className="text-md font-medium text-gray-900 mb-3">
            Optional Fields
          </h3>
          <div className="space-y-4">
            {providerInfo.optional_fields.map((field) => (
              <FieldRenderer
                key={field.name}
                field={field}
                value={config[field.name]}
                validation={validation}
                onChange={handleFieldChange}
              />
            ))}
          </div>
        </div>
      )}

      {/* No fields message */}
      {!hasRequiredFields && !hasOptionalFields && (
        <div className="text-center py-8 text-gray-500">
          <p>This provider has no configurable fields</p>
        </div>
      )}

      {/* Validation Status */}
      <div className="border-t pt-4">
        <div className="flex items-center justify-between">
          <h3 className="text-md font-medium text-gray-900">
            Configuration Status
          </h3>
          {isValidating && (
            <div className="flex items-center text-sm text-gray-600">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
              Validating...
            </div>
          )}
        </div>

        {validation && (
          <div className="mt-3">
            {validation.valid ? (
              <div className="p-3 bg-green-50 border border-green-200 rounded-md">
                <div className="flex items-center">
                  <span className="text-green-600">✓</span>
                  <span className="ml-2 text-green-800 font-medium">
                    Configuration is valid
                  </span>
                </div>
              </div>
            ) : (
              <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                <div className="flex items-start">
                  <span className="text-red-600 mt-0.5">⚠</span>
                  <div className="ml-2">
                    <div className="text-red-800 font-medium mb-1">
                      Configuration errors:
                    </div>
                    <ul className="text-red-700 text-sm space-y-1">
                      {validation.errors.map((error, index) => (
                        <li key={index}>• {error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {validation.warnings.length > 0 && (
              <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                <div className="flex items-start">
                  <span className="text-yellow-600 mt-0.5">⚠</span>
                  <div className="ml-2">
                    <div className="text-yellow-800 font-medium mb-1">
                      Warnings:
                    </div>
                    <ul className="text-yellow-700 text-sm space-y-1">
                      {validation.warnings.map((warning, index) => (
                        <li key={index}>• {warning}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};