import { createPortal } from 'react-dom';

import { BACKEND_URL } from '@/config';

/**
 * AppStatus - Overlay shown when backend is disconnected
 * Uses Portal to render to document.body, ensuring it appears above
 * all content including Radix UI dialogs which also use portals.
 * Has a frosted glass effect to obscure and block interaction with content behind.
 */
export const AppStatus = ({ connected }: { connected: boolean }) => {
  if (connected) {
    return null;
  }

  return createPortal(
    <div className="bg-background/95 fixed inset-0 z-[100] flex items-center justify-center backdrop-blur-md">
      <div className="text-center">
        <div className="text-destructive mb-4 text-6xl">⚠️</div>
        <h1 className="text-foreground mb-4 text-2xl font-bold">
          Backend Disconnected
        </h1>
        <p className="text-muted-foreground mb-4">
          Cannot connect to the TTS backend server at {BACKEND_URL}
        </p>
        <p className="text-muted-foreground text-sm">
          Make sure the backend server is running:{' '}
          <code className="bg-muted rounded px-1 py-0.5">make gui-server</code>
        </p>
      </div>
    </div>,
    document.body
  );
};

/**
 * AppLoading - Overlay shown while backend is starting up
 * Uses Portal to render to document.body, ensuring it appears above
 * all content including Radix UI dialogs which also use portals.
 * Has a frosted glass effect to obscure and block interaction with content behind.
 */
export const AppLoading = () =>
  createPortal(
    <div className="bg-background/95 fixed inset-0 z-[100] flex items-center justify-center backdrop-blur-md">
      <div className="text-center">
        <div className="border-primary mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-b-2"></div>
        <p className="text-muted-foreground">Connecting to backend...</p>
      </div>
    </div>,
    document.body
  );
