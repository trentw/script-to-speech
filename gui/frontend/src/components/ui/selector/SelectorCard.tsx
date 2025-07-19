import React from 'react';
import { Check } from 'lucide-react';

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
      className={`w-full text-left p-3 rounded-lg border transition-all duration-200 cursor-pointer hover:border-accent hover:bg-accent/5 hover:shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent ${
        isSelected
          ? 'border-primary bg-primary/5 shadow-sm'
          : 'border-border bg-background'
      }`}
    >
      <div className="flex items-center gap-3">
        {/* Avatar */}
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm font-semibold shrink-0">
          {renderAvatar ? (
            renderAvatar(item)
          ) : (
            renderPrimary(item).charAt(0).toUpperCase()
          )}
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm truncate">
            {renderPrimary(item)}
          </div>
          {renderSecondary && (
            <div className="text-xs text-muted-foreground truncate">
              {renderSecondary(item)}
            </div>
          )}
          {renderDescription && (
            <div className="text-xs text-muted-foreground mt-1 line-clamp-2 whitespace-pre-line">
              {renderDescription(item).split(/(\*\*[^*]+\*\*)/).map((part, index) => {
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
          <div className="shrink-0 w-5 h-5 rounded-full bg-primary flex items-center justify-center">
            <Check className="w-3 h-3 text-primary-foreground" />
          </div>
        )}
      </div>
    </button>
  );
}