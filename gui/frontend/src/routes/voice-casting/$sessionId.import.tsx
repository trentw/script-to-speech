import { createFileRoute } from '@tanstack/react-router';

import { RouteError } from '@/components/errors';
import { YamlImportPanel } from '@/components/voice-casting';
import { useVoiceCastingNavigation } from '@/hooks/useVoiceCastingNavigation';

export const Route = createFileRoute('/voice-casting/$sessionId/import')({
  component: YamlImportRoute,
  errorComponent: RouteError,
});

function YamlImportRoute() {
  const { sessionId } = Route.useParams();
  const { navigateToSession } = useVoiceCastingNavigation();

  const handleBack = () => {
    navigateToSession(sessionId);
  };

  const handleImportSuccess = () => {
    navigateToSession(sessionId);
  };

  return (
    <YamlImportPanel
      sessionId={sessionId}
      onBack={handleBack}
      onImportSuccess={handleImportSuccess}
    />
  );
}
