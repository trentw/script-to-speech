import type { ProviderInfo, VoiceEntry } from '../../types';
import { ConfigurationPanel } from '../ConfigurationPanel';

export const PanelContent = ({
  providers,
  voiceLibrary,
  voiceCounts,
  providerErrors,
  loading,
  onProviderChange,
  onVoiceSelect,
  onConfigChange,
}: {
  providers: ProviderInfo[];
  voiceLibrary: Record<string, VoiceEntry[]>;
  voiceCounts: Record<string, number>;
  providerErrors: Record<string, boolean>;
  loading: boolean;
  onProviderChange: (provider: string) => void;
  onVoiceSelect: (voice: VoiceEntry) => void;
  onConfigChange: (config: Record<string, unknown>) => void;
}) => {
  return (
    <ConfigurationPanel
      providers={providers || []}
      voiceLibrary={voiceLibrary}
      voiceCounts={voiceCounts}
      providerErrors={providerErrors}
      loading={loading}
      onProviderChange={onProviderChange}
      onVoiceSelect={onVoiceSelect}
      onConfigChange={onConfigChange}
    />
  );
};
