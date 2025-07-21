import { ChevronRight, User } from 'lucide-react';
import React from 'react';

import { Button } from '@/components/ui/button';

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
      className="hover:bg-accent hover:text-accent-foreground hover:border-accent h-auto w-full cursor-pointer p-0 transition-all duration-200"
      onClick={onClick}
    >
      <div className="flex w-full items-center justify-between p-3">
        <div className="flex items-center gap-3">
          {/* Avatar */}
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-sm font-semibold text-white">
            {selectedItem && renderAvatar ? (
              renderAvatar(selectedItem)
            ) : selectedItem ? (
              renderPrimary(selectedItem).charAt(0).toUpperCase()
            ) : (
              <User className="h-4 w-4" />
            )}
          </div>

          {/* Content */}
          <div className="min-w-0 flex-1 text-left">
            <div className="truncate text-sm font-medium">
              {selectedItem ? renderPrimary(selectedItem) : placeholder}
            </div>
            {selectedItem && renderSecondary ? (
              <div className="text-muted-foreground truncate text-xs">
                {renderSecondary(selectedItem)}
              </div>
            ) : !selectedItem && availableCount > 0 ? (
              <div className="text-muted-foreground truncate text-xs">
                Choose from {availableCount} available option
                {availableCount !== 1 ? 's' : ''}
              </div>
            ) : null}
          </div>
        </div>

        <ChevronRight className="text-muted-foreground h-4 w-4 shrink-0 opacity-70" />
      </div>
    </Button>
  );
}
