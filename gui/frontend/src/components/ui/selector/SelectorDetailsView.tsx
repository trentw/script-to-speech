import { Badge } from '@/components/ui/badge';

interface SelectorDetailsViewProps<T> {
  selectedItem?: T;
  renderDescription?: (item: T) => string;
  renderTags?: (
    item: T
  ) => Array<{ label: string; variant?: 'default' | 'secondary' | 'outline' }>;
  className?: string;
}

export function SelectorDetailsView<T>({
  selectedItem,
  renderDescription,
  renderTags,
  className = '',
}: SelectorDetailsViewProps<T>) {
  if (!selectedItem) return null;

  const description = renderDescription?.(selectedItem);
  const tags = renderTags?.(selectedItem) || [];

  if (!description && tags.length === 0) return null;

  return (
    <div className={`bg-muted/30 space-y-2 rounded-lg p-3 ${className}`}>
      {/* Description */}
      {description && (
        <p className="text-muted-foreground text-xs">{description}</p>
      )}

      {/* Tags */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {tags.map((tag, index) => (
            <Badge
              key={index}
              variant={tag.variant || 'secondary'}
              className="px-1.5 py-0 text-xs"
            >
              {tag.label}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
