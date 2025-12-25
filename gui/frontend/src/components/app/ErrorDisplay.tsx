import { useUIState } from '../../stores/appStore';
import { appButtonVariants } from '../ui/button-variants';

export const ErrorDisplay = () => {
  const { error, clearError } = useUIState();

  if (!error) return null;

  return (
    <div className="absolute right-4 bottom-4 left-4 z-50">
      <div className="bg-destructive/10 border-destructive/20 supports-[backdrop-filter]:bg-destructive/5 rounded-lg border p-4 backdrop-blur">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-destructive font-medium">Generation Error</h4>
            <p className="text-destructive/80 mt-1 text-sm">{error}</p>
          </div>
          <button
            className={`${appButtonVariants({ variant: 'list-action', size: 'sm' })} text-destructive hover:text-destructive/80 border-destructive/20 hover:bg-destructive/10 border`}
            onClick={clearError}
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
};
