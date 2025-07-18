
import { useConfiguration } from '../../stores/appStore';

export const ProviderSelector = ({
  providers,
  handleProviderChange,
}: {
  providers: any[];
  handleProviderChange: (provider: string) => void;
}) => {
  const { selectedProvider } = useConfiguration();

  return (
    <div className="flex items-center space-x-2">
      <label className="text-sm text-muted-foreground">Provider:</label>
      <select
        className="px-3 py-2 border border-border rounded-lg bg-background text-foreground hover:border-accent transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
        value={selectedProvider || ''}
        onChange={(e) => handleProviderChange(e.target.value)}
      >
        <option value="" key="select-provider-placeholder">Select Provider</option>
        {providers?.map((provider) => (
          <option key={provider.identifier} value={provider.identifier}>
            {provider.name}
          </option>
        ))}
      </select>
      {selectedProvider && (
        <div className="text-xs text-muted-foreground bg-muted/30 px-2 py-1 rounded-md">
          {providers?.find(p => p.identifier === selectedProvider)?.description || 
           `${selectedProvider.charAt(0).toUpperCase() + selectedProvider.slice(1)} TTS`}
        </div>
      )}
    </div>
  );
};
