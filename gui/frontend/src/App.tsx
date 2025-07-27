import { useQueryClient } from '@tanstack/react-query';
import { RouterProvider } from '@tanstack/react-router';
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools';
import { useMemo } from 'react';

import { AudioServiceProvider } from './providers';
import { createAppRouter } from './router';

function App() {
  const queryClient = useQueryClient();
  const router = useMemo(() => createAppRouter(queryClient), [queryClient]);

  return (
    <AudioServiceProvider>
      <RouterProvider router={router} />
      <TanStackRouterDevtools router={router} />
    </AudioServiceProvider>
  );
}

export default App;
