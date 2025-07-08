import React from 'react';

interface TextInputProps {
  value: string;
  onChange: (text: string) => void;
  placeholder?: string;
}

export const TextInput: React.FC<TextInputProps> = ({
  value,
  onChange,
  placeholder = "Enter text to convert to speech..."
}) => {
  return (
    <div className="form-group">
      <textarea
        className="input-field resize-none"
        rows={4}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
      <div className="flex justify-between items-center mt-2">
        <span className="text-sm text-gray-500">
          {value.length} characters
        </span>
        {value.length > 1000 && (
          <span className="text-sm text-amber-600">
            Long text may take more time to generate
          </span>
        )}
      </div>
    </div>
  );
};