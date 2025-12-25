import { ChevronDown, CirclePlus, Settings } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { appButtonVariants } from '@/components/ui/button-variants';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useProviderMetadata } from '@/hooks/queries/useProviderMetadata';
import { cn } from '@/lib/utils';
import { FieldType, type ProviderField } from '@/types';

import { FormField } from './FormField';
import { ProviderAvatar } from './ProviderAvatar';

// Validation function shared between form and card components
function validateFieldValue(
  field: ProviderField,
  value: unknown
): string | null {
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
}

interface CustomVoiceCardFormProps {
  provider: string;
  currentConfig?: Record<string, unknown>;
  onConfigChange: (config: Record<string, unknown>) => void;
}

interface CustomVoiceCardProps {
  provider: string;
  onAssignVoice: (config: Record<string, unknown>) => void;
  currentConfig?: Record<string, unknown>;
  className?: string;
}

// Internal form component for inline display
function CustomVoiceCardForm({
  provider,
  currentConfig = {},
  onConfigChange,
}: CustomVoiceCardFormProps) {
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

  // Notify parent of form changes
  useEffect(() => {
    onConfigChange(formValues);
  }, [formValues, onConfigChange]);

  const handleFieldChange = (fieldName: string, value: unknown) => {
    // Find the field definition
    const field = providerInfo?.required_fields.find(
      (f) => f.name === fieldName
    );
    if (field) {
      // Validate the new value
      const error = validateFieldValue(field, value);
      if (error) {
        setErrors((prev) => ({ ...prev, [fieldName]: error }));
        // Still update the value to show user input, but with error
        setFormValues((prev) => ({
          ...prev,
          [fieldName]: value,
        }));
        return;
      }
    }

    // Update value and clear any existing error
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

  if (isLoading) {
    return (
      <div className="p-4 text-center">
        <p className="text-muted-foreground text-sm">
          Loading configuration...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center">
        <p className="text-destructive text-xs">
          Failed to load provider configuration
        </p>
      </div>
    );
  }

  if (!providerInfo) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="text-muted-foreground text-xs">
        Configure the required fields for your custom voice
      </div>

      <div className="space-y-3">
        {providerInfo.required_fields.map((field) => (
          <FormField
            key={field.name}
            field={field}
            value={formValues[field.name] ?? field.default ?? ''}
            error={errors[field.name]}
            onChange={(value) => handleFieldChange(field.name, value)}
          />
        ))}
      </div>
    </div>
  );
}

export function CustomVoiceCard({
  provider,
  onAssignVoice,
  currentConfig,
  className,
}: CustomVoiceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [formConfig, setFormConfig] = useState<Record<string, unknown>>(
    currentConfig || {}
  );
  const { data: providerInfo } = useProviderMetadata(provider);

  // Check if form is valid (all required fields are filled and pass validation)
  const isFormValid = () => {
    if (!providerInfo) return false;

    return providerInfo.required_fields.every((field) => {
      const value = formConfig[field.name];
      // Check if value exists
      if (value === undefined || value === null || value === '') return false;
      // Check if value is valid
      return validateFieldValue(field, value) === null;
    });
  };

  const handleCardClick = (e: React.MouseEvent) => {
    // Don't toggle if clicking on interactive elements
    const target = e.target as HTMLElement;
    if (
      target.closest('button') ||
      target.closest('[role="button"]') ||
      target.closest('input') ||
      target.closest('select') ||
      target.closest('textarea') ||
      target.closest('[role="combobox"]') ||
      target.closest('[role="switch"]')
    ) {
      return;
    }
    setIsExpanded(!isExpanded);
  };

  const handleCardKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setIsExpanded(!isExpanded);
    }
  };

  const handleConfigureClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsExpanded(true);
  };

  const handleAssignClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isFormValid()) {
      onAssignVoice(formConfig);
      setIsExpanded(false);
    }
  };

  const handleConfigChange = (config: Record<string, unknown>) => {
    setFormConfig(config);
  };

  return (
    <div
      className={cn(
        'bg-muted/50 cursor-pointer rounded-lg border transition-all hover:shadow-sm',
        isExpanded && 'shadow-md',
        className
      )}
      onClick={handleCardClick}
      onKeyDown={handleCardKeyDown}
      role="button"
      tabIndex={0}
      aria-label={`${isExpanded ? 'Collapse' : 'Expand'} custom voice card details`}
    >
      {/* Main Content */}
      <div className="p-3">
        <div className="flex items-center justify-between">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <ProviderAvatar provider={provider} size="sm" />
            <div className="min-w-0 flex-1 space-y-1">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium">Custom Voice</p>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Settings className="text-muted-foreground h-3 w-3" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Custom voice configuration</p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <p className="text-muted-foreground text-xs">
                {isExpanded
                  ? 'Configure your custom voice'
                  : 'Custom configuration'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            {!isExpanded ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className={appButtonVariants({
                      variant: 'list-action',
                      size: 'sm',
                    })}
                    onClick={handleConfigureClick}
                  >
                    <Settings className="h-3 w-3" />
                    Configure
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Configure custom voice</p>
                </TooltipContent>
              </Tooltip>
            ) : (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className={appButtonVariants({
                      variant: 'list-action',
                      size: 'sm',
                    })}
                    onClick={handleAssignClick}
                    disabled={!isFormValid()}
                  >
                    <CirclePlus className="h-3 w-3" />
                    Assign
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Assign voice</p>
                </TooltipContent>
              </Tooltip>
            )}
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  className={cn(
                    appButtonVariants({
                      variant: 'list-action',
                      size: 'icon-sm',
                    }),
                    'transition-transform duration-200',
                    isExpanded && 'rotate-180'
                  )}
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsExpanded(!isExpanded);
                  }}
                >
                  <ChevronDown className="h-3 w-3" />
                </button>
              </TooltipTrigger>
              <TooltipContent>
                <p>
                  {isExpanded ? 'Hide configuration' : 'Show configuration'}
                </p>
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      <div
        className={cn(
          'overflow-hidden transition-all duration-300 ease-in-out',
          isExpanded ? 'max-h-96' : 'max-h-0'
        )}
      >
        <div className="border-t px-3 pt-2 pb-3">
          <CustomVoiceCardForm
            provider={provider}
            currentConfig={currentConfig}
            onConfigChange={handleConfigChange}
          />
        </div>
      </div>
    </div>
  );
}
