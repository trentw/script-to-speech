import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SelectorPanelProps {
  isOpen: boolean;
  title: string;
  onBack: () => void;
  children: React.ReactNode;
}

export const SelectorPanel: React.FC<SelectorPanelProps> = ({
  isOpen,
  title,
  onBack,
  children,
}) => {
  return (
    <div className={`absolute inset-0 h-full overflow-y-auto transform transition-transform duration-300 ease-in-out ${
      isOpen ? 'translate-x-0' : 'translate-x-full'
    }`}>
      {isOpen && (
        <div className="p-4 space-y-4">
          {/* Header */}
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={onBack}
              className="shrink-0 p-1.5 h-auto"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <h2 className="text-sm font-medium text-foreground">{title}</h2>
          </div>
          
          {/* Content */}
          <div className="space-y-2">
            {children}
          </div>
        </div>
      )}
    </div>
  );
};