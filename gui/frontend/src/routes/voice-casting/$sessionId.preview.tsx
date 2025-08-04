import { createFileRoute } from '@tanstack/react-router';

import { RouteError } from '@/components/errors';
import { YamlPreview } from '@/components/voice-casting';
import { useVoiceCastingNavigation } from '@/hooks/useVoiceCastingNavigation';

export const Route = createFileRoute('/voice-casting/$sessionId/preview')({
  component: YamlPreviewRoute,
  errorComponent: RouteError,
});

function YamlPreviewRoute() {
  const { sessionId } = Route.useParams();
  const { navigateToSession } = useVoiceCastingNavigation();

  const handleBack = () => {
    navigateToSession(sessionId);
  };

  return <YamlPreview onBack={handleBack} />;
}
