import { appButtonVariants } from '@/components/ui/button-variants';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

import { useUserInput } from '../../stores/appStore';

export const MainContent = ({
  handleGenerate,
  isGenerating,
}: {
  handleGenerate: () => void;
  isGenerating: boolean;
}) => {
  const { text, setText } = useUserInput();

  return (
    <TooltipProvider>
      <div className="flex h-full flex-col">
        {/* Text Input Area */}
        <div className="flex-1 p-6">
          <div className="flex h-full flex-col">
            <div className="mb-4 flex-1">
              <textarea
                className="border-border bg-background placeholder:text-muted-foreground focus:ring-primary h-full min-h-[400px] w-full resize-none rounded-lg border p-4 text-lg transition-all duration-200 focus:border-transparent focus:ring-2 focus:outline-none"
                placeholder="Write something to say..."
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
            </div>

            {/* Warning and Generate button */}
            <div className="flex items-center justify-between pt-2">
              <div className="text-muted-foreground text-sm">
                {text.length > 1000 && (
                  <span className="flex items-center gap-1 text-amber-600">
                    <svg
                      className="h-4 w-4"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                        clipRule="evenodd"
                      />
                    </svg>
                    Long text may take more time to generate
                  </span>
                )}
              </div>
              <div className="flex items-center gap-4">
                {/* Character count indicator */}
                <div className="text-muted-foreground bg-background border-border min-w-[100px] rounded-md border px-4 py-1.5 text-center text-xs font-medium">
                  <span
                    className={
                      text.length > 4000
                        ? 'text-destructive'
                        : text.length > 2000
                          ? 'text-amber-600'
                          : 'text-muted-foreground'
                    }
                  >
                    {text.length.toLocaleString()} / 5,000
                  </span>
                </div>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      className={appButtonVariants({
                        variant: 'primary',
                        size: 'lg',
                      })}
                      onClick={handleGenerate}
                      disabled={!text.trim() || isGenerating}
                    >
                      {isGenerating ? (
                        <div className="flex items-center space-x-2">
                          <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
                          <span>Generating...</span>
                        </div>
                      ) : (
                        <span>Generate speech</span>
                      )}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>
                      {navigator.userAgent.includes('Mac') ? '⌘' : 'Ctrl'}+Enter
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
            </div>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
};
