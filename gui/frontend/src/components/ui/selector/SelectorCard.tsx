import { Check } from 'lucide-react';
import React from 'react';

interface SelectorCardProps<T> {
  item: T;
  isSelected: boolean;
  onSelect: (item: T) => void;
  renderAvatar?: (item: T) => React.ReactNode;
  renderPrimary: (item: T) => string;
  renderSecondary?: (item: T) => string;
  renderDescription?: (item: T) => string;
}

export function SelectorCard<T>({
  item,
  isSelected,
  onSelect,
  renderAvatar,
  renderPrimary,
  renderSecondary,
  renderDescription,
}: SelectorCardProps<T>) {
  return (
    <button
      onClick={() => onSelect(item)}
      className={`hover:border-accent hover:bg-accent/5 focus:ring-primary w-full cursor-pointer rounded-lg border p-3 text-left transition-all duration-200 hover:shadow-sm focus:border-transparent focus:ring-2 focus:outline-none ${
        isSelected
          ? 'border-primary bg-primary/5 shadow-sm'
          : 'border-border bg-background'
      }`}
    >
      <div className="flex items-center gap-3">
        {/* Avatar - renderAvatar should return a JSX element */}
        {renderAvatar ? (
          renderAvatar(item)
        ) : (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-gray-200/50 bg-white p-1">
            <span className="text-sm font-semibold text-gray-700">
              {renderPrimary(item).charAt(0).toUpperCase()}
            </span>
          </div>
        )}

        {/* Content */}
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium">
            {renderPrimary(item)}
          </div>
          {renderSecondary && (
            <div className="text-muted-foreground truncate text-xs">
              {renderSecondary(item)}
            </div>
          )}
          {renderDescription && (
            <div className="text-muted-foreground mt-1 line-clamp-2 text-xs whitespace-pre-line">
              {renderDescription(item)
                .split(/(\*\*[^*]+\*\*)/)
                .map((part, index) => {
                  if (part.startsWith('**') && part.endsWith('**')) {
                    return (
                      <span key={index} className="font-mono">
                        {part.slice(2, -2)}
                      </span>
                    );
                  }
                  return part;
                })}
            </div>
          )}
        </div>

        {/* Selection indicator */}
        {isSelected && (
          <div className="bg-primary flex h-5 w-5 shrink-0 items-center justify-center rounded-full">
            <Check className="text-primary-foreground h-3 w-3" />
          </div>
        )}
      </div>
    </button>
  );
}
