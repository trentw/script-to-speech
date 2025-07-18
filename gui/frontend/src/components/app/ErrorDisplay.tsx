
import { useUIState } from '../../stores/appStore';
import { appButtonVariants } from '../ui/button-variants';

export const ErrorDisplay = () => {
  const { error, clearError } = useUIState();

  if (!error) return null;

  return (
    <div className="absolute bottom-4 left-4 right-4 z-50">
      <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-lg backdrop-blur supports-[backdrop-filter]:bg-destructive/5">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="font-medium text-destructive">Generation Error</h4>
            <p className="text-sm text-destructive/80 mt-1">{error}</p>
          </div>
          <button
            className={`${appButtonVariants({ variant: "list-action", size: "sm" })} text-destructive hover:text-destructive/80 border border-destructive/20 hover:bg-destructive/10`}
            onClick={clearError}
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
};
