import React from 'react';
import { Button } from '@/components/ui/button';
import { ChevronRight, User } from 'lucide-react';

interface SelectorButtonProps<T> {
  selectedItem?: T;
  placeholder: string;
  onClick: () => void;
  renderAvatar?: (item: T) => React.ReactNode;
  renderPrimary: (item: T) => string;
  renderSecondary?: (item: T) => string;
  availableCount?: number;
}

export function SelectorButton<T>({
  selectedItem,
  placeholder,
  onClick,
  renderAvatar,
  renderPrimary,
  renderSecondary,
  availableCount = 0,
}: SelectorButtonProps<T>) {
  return (
    <Button
      variant="outline"
      className="w-full h-auto p-0 hover:bg-accent hover:text-accent-foreground hover:border-accent transition-all duration-200 cursor-pointer"
      onClick={onClick}
    >
      <div className="flex items-center justify-between w-full p-3">
        <div className="flex items-center gap-3">
          {/* Avatar */}
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm font-semibold">
            {selectedItem && renderAvatar ? (
              renderAvatar(selectedItem)
            ) : selectedItem ? (
              renderPrimary(selectedItem).charAt(0).toUpperCase()
            ) : (
              <User className="w-4 h-4" />
            )}
          </div>
          
          {/* Content */}
          <div className="text-left flex-1 min-w-0">
            <div className="font-medium text-sm truncate">
              {selectedItem ? renderPrimary(selectedItem) : placeholder}
            </div>
            {selectedItem && renderSecondary ? (
              <div className="text-xs text-muted-foreground truncate">
                {renderSecondary(selectedItem)}
              </div>
            ) : !selectedItem && availableCount > 0 ? (
              <div className="text-xs text-muted-foreground truncate">
                Choose from {availableCount} available option{availableCount !== 1 ? 's' : ''}
              </div>
            ) : null}
          </div>
        </div>
        
        <ChevronRight className="h-4 w-4 opacity-70 shrink-0 text-muted-foreground" />
      </div>
    </Button>
  );
}