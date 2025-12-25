import { cn } from '@/lib/utils';
import { FieldType, type ProviderField } from '@/types';

interface FormFieldProps {
  field: ProviderField;
  value: unknown;
  error?: string;
  onChange: (value: unknown) => void;
}

export function FormField({ field, value, error, onChange }: FormFieldProps) {
  const label = (
    <label
      htmlFor={field.name}
      className="text-muted-foreground text-xs font-medium"
    >
      {field.name.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
      {field.required && <span className="text-destructive ml-1">*</span>}
    </label>
  );

  const fieldClasses = cn(
    'w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm',
    'ring-offset-background placeholder:text-muted-foreground',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
    'disabled:cursor-not-allowed disabled:opacity-50',
    error ? 'border-destructive' : ''
  );

  switch (field.type) {
    case FieldType.STRING:
      if (field.options) {
        return (
          <div className="space-y-1">
            {label}
            <select
              id={field.name}
              value={value as string}
              onChange={(e) => onChange(e.target.value)}
              className={fieldClasses}
            >
              <option value="">Select {field.name}</option>
              {field.options.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            {error && <p className="text-destructive text-xs">{error}</p>}
          </div>
        );
      }
      return (
        <div className="space-y-1">
          {label}
          <input
            id={field.name}
            type="text"
            value={value as string}
            onChange={(e) => onChange(e.target.value)}
            className={fieldClasses}
            placeholder={field.description}
          />
          {error && <p className="text-destructive text-xs">{error}</p>}
        </div>
      );

    case FieldType.INTEGER:
    case FieldType.FLOAT:
      return (
        <div className="space-y-1">
          {label}
          <input
            id={field.name}
            type="number"
            value={value as number}
            onChange={(e) => {
              const val =
                field.type === FieldType.INTEGER
                  ? parseInt(e.target.value, 10)
                  : parseFloat(e.target.value);
              onChange(isNaN(val) ? '' : val);
            }}
            step={field.type === FieldType.FLOAT ? 'any' : '1'}
            min={field.min_value}
            max={field.max_value}
            className={fieldClasses}
            placeholder={field.description}
          />
          {error && <p className="text-destructive text-xs">{error}</p>}
        </div>
      );

    case FieldType.BOOLEAN:
      return (
        <div className="flex items-center space-x-2">
          <input
            id={field.name}
            type="checkbox"
            checked={value as boolean}
            onChange={(e) => onChange(e.target.checked)}
            className="border-input focus:ring-ring h-4 w-4 rounded border focus:ring-2 focus:ring-offset-2 focus:outline-none"
          />
          {label}
        </div>
      );

    default:
      return null;
  }
}
