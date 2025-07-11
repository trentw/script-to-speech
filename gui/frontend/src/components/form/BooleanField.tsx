import React from 'react';
import type { ProviderField } from '../../types';

interface BooleanFieldProps {
  field: ProviderField;
  value: boolean;
  onChange: (value: boolean) => void;
}

export const BooleanField: React.FC<BooleanFieldProps> = ({
  field,
  value,
  onChange
}) => {
  return (
    <div className="flex items-center">
      <input
        type="checkbox"
        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        checked={!!value}
        onChange={(e) => onChange(e.target.checked)}
      />
      <label className="ml-2 text-sm text-gray-700">
        {field.description || `Enable ${field.name}`}
      </label>
    </div>
  );
};