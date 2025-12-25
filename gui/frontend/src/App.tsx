import { useQueryClient } from '@tanstack/react-query';
import { RouterProvider } from '@tanstack/react-router';
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools';
import { useMemo } from 'react';

import { BackendGate } from './components/app/BackendGate';
import { AudioServiceProvider } from './providers';
import { createAppRouter } from './router';

function App() {
  const queryClient = useQueryClient();
  const router = useMemo(() => createAppRouter(queryClient), [queryClient]);

  return (
    <AudioServiceProvider>
      <BackendGate>
        <RouterProvider router={router} />
        <TanStackRouterDevtools router={router} />
      </BackendGate>
    </AudioServiceProvider>
  );
}

export default App;
