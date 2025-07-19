
import { useUserInput } from '../../stores/appStore';
import { appButtonVariants } from '@/components/ui/button-variants';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

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
      <div className="flex flex-col h-full">
      {/* Text Input Area */}
      <div className="flex-1 p-6">
        <div className="h-full flex flex-col">
          <div className="flex-1 mb-4">
            <textarea
              className="w-full h-full min-h-[400px] resize-none border border-border rounded-lg p-4 bg-background text-lg placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all duration-200"
              placeholder="Write something to say..."
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
          </div>
          
          {/* Warning and Generate button */}
          <div className="flex items-center justify-between pt-2">
            <div className="text-sm text-muted-foreground">
              {text.length > 1000 && (
                <span className="text-amber-600 flex items-center gap-1">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  Long text may take more time to generate
                </span>
              )}
            </div>
            <div className="flex items-center gap-4">
              {/* Character count indicator */}
              <div className="text-xs px-4 py-1.5 rounded-md font-medium border text-muted-foreground bg-background border-border min-w-[100px] text-center">
                <span className={
                  text.length > 4000 ? 'text-destructive' :
                  text.length > 2000 ? 'text-amber-600' :
                  'text-muted-foreground'
                }>
                  {text.length.toLocaleString()} / 5,000
                </span>
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className={appButtonVariants({ variant: "primary", size: "lg" })}
                    onClick={handleGenerate}
                    disabled={!text.trim() || isGenerating}
                  >
                    {isGenerating ? (
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
                        <span>Generating...</span>
                      </div>
                    ) : (
                      <span>Generate speech</span>
                    )}
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{navigator.userAgent.includes('Mac') ? '⌘' : 'Ctrl'}+Enter</p>
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
