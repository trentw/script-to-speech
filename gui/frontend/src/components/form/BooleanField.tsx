import React from 'react';

import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';

import type { ProviderField } from '../../types';

interface BooleanFieldProps {
  field: ProviderField;
  value: boolean;
  onChange: (value: boolean) => void;
}

export const BooleanField: React.FC<BooleanFieldProps> = ({
  field,
  value,
  onChange,
}) => {
  return (
    <div className="flex items-center justify-between">
      <div className="space-y-0.5">
        <Label className="text-foreground text-sm font-medium">
          {field.description || field.name}
        </Label>
        {field.description && field.description !== field.name && (
          <p className="text-muted-foreground text-xs">
            Toggle to {value ? 'disable' : 'enable'} this feature
          </p>
        )}
      </div>
      <Switch
        checked={!!value}
        onCheckedChange={onChange}
        aria-label={field.description || `Toggle ${field.name}`}
      />
    </div>
  );
};
