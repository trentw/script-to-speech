
import { ConfigurationPanel } from '../ConfigurationPanel';
import type { VoiceEntry } from '../../types';

export const PanelContent = ({
  providers,
  voiceLibrary,
  loading,
  onProviderChange,
  onVoiceSelect,
  onConfigChange,
}: {
  providers: any[];
  voiceLibrary: Record<string, VoiceEntry[]>;
  loading: boolean;
  onProviderChange: (provider: string) => void;
  onVoiceSelect: (voice: VoiceEntry) => void;
  onConfigChange: (config: Record<string, unknown>) => void;
}) => {
  return (
    <ConfigurationPanel
      providers={providers || []}
      voiceLibrary={voiceLibrary}
      loading={loading}
      onProviderChange={onProviderChange}
      onVoiceSelect={onVoiceSelect}
      onConfigChange={onConfigChange}
    />
  );
};
