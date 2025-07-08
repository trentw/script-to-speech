import React, { useState, useEffect } from 'react';
import type { ProviderInfo, ProviderField, ValidationResult } from '../types';
import { FieldType } from '../types';
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

  const renderField = (field: ProviderField) => {
    const value = config[field.name] || '';
    const hasError = validation?.errors.some(error => 
      error.toLowerCase().includes(field.name.toLowerCase())
    );

    switch (field.type) {
      case FieldType.STRING:
        if (field.options && field.options.length > 0) {
          // Dropdown for string fields with options
          return (
            <select
              className={`select-field ${hasError ? 'border-red-500' : ''}`}
              value={value}
              onChange={(e) => updateField(field.name, e.target.value)}
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
              onChange={(e) => updateField(field.name, e.target.value)}
              placeholder={field.description || `Enter ${field.name}`}
            />
          );
        }

      case FieldType.INTEGER:
        return (
          <input
            type="number"
            step="1"
            className={`input-field ${hasError ? 'border-red-500' : ''}`}
            value={value}
            onChange={(e) => updateField(field.name, parseInt(e.target.value) || '')}
            min={field.min_value}
            max={field.max_value}
            placeholder={field.description || `Enter ${field.name}`}
          />
        );

      case FieldType.FLOAT:
        return (
          <input
            type="number"
            step="0.1"
            className={`input-field ${hasError ? 'border-red-500' : ''}`}
            value={value}
            onChange={(e) => updateField(field.name, parseFloat(e.target.value) || '')}
            min={field.min_value}
            max={field.max_value}
            placeholder={field.description || `Enter ${field.name}`}
          />
        );

      case FieldType.BOOLEAN:
        return (
          <div className="flex items-center">
            <input
              type="checkbox"
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              checked={!!value}
              onChange={(e) => updateField(field.name, e.target.checked)}
            />
            <label className="ml-2 text-sm text-gray-700">
              {field.description || `Enable ${field.name}`}
            </label>
          </div>
        );

      case FieldType.LIST:
        return (
          <div>
            <textarea
              className={`input-field ${hasError ? 'border-red-500' : ''}`}
              rows={3}
              value={Array.isArray(value) ? JSON.stringify(value, null, 2) : value}
              onChange={(e) => {
                try {
                  const parsed = JSON.parse(e.target.value);
                  updateField(field.name, parsed);
                } catch {
                  // Keep as string until valid JSON
                  updateField(field.name, e.target.value);
                }
              }}
              placeholder={field.description || `Enter ${field.name} as JSON array`}
            />
            <p className="text-xs text-gray-500 mt-1">
              Enter as JSON array, e.g., ["item1", "item2"]
            </p>
          </div>
        );

      case FieldType.DICT:
        return (
          <div>
            <textarea
              className={`input-field ${hasError ? 'border-red-500' : ''}`}
              rows={4}
              value={typeof value === 'object' ? JSON.stringify(value, null, 2) : value}
              onChange={(e) => {
                try {
                  const parsed = JSON.parse(e.target.value);
                  updateField(field.name, parsed);
                } catch {
                  // Keep as string until valid JSON
                  updateField(field.name, e.target.value);
                }
              }}
              placeholder={field.description || `Enter ${field.name} as JSON object`}
            />
            <p className="text-xs text-gray-500 mt-1">
              Enter as JSON object, e.g., {`{"key": "value"}`}
            </p>
          </div>
        );

      default:
        return (
          <input
            type="text"
            className={`input-field ${hasError ? 'border-red-500' : ''}`}
            value={value}
            onChange={(e) => updateField(field.name, e.target.value)}
            placeholder={field.description || `Enter ${field.name}`}
          />
        );
    }
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
              <div key={field.name} className="form-group">
                <label className="form-label">
                  {field.name}
                  <span className="text-red-500 ml-1">*</span>
                  {field.description && (
                    <span className="text-gray-500 font-normal ml-2">
                      - {field.description}
                    </span>
                  )}
                </label>
                {renderField(field)}
                {field.min_value !== undefined && field.max_value !== undefined && (
                  <p className="text-xs text-gray-500 mt-1">
                    Range: {field.min_value} - {field.max_value}
                  </p>
                )}
              </div>
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
              <div key={field.name} className="form-group">
                <label className="form-label">
                  {field.name}
                  {field.description && (
                    <span className="text-gray-500 font-normal ml-2">
                      - {field.description}
                    </span>
                  )}
                </label>
                {renderField(field)}
                {field.min_value !== undefined && field.max_value !== undefined && (
                  <p className="text-xs text-gray-500 mt-1">
                    Range: {field.min_value} - {field.max_value}
                  </p>
                )}
                {field.default !== undefined && (
                  <p className="text-xs text-gray-500 mt-1">
                    Default: {JSON.stringify(field.default)}
                  </p>
                )}
              </div>
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