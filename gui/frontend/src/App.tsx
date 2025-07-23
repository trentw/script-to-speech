import { useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { RouterProvider } from '@tanstack/react-router';
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools';

import { createAppRouter } from './router';

function App() {
  const queryClient = useQueryClient();
  const router = useMemo(() => createAppRouter(queryClient), [queryClient]);

  return (
    <>
      <RouterProvider router={router} />
      <TanStackRouterDevtools router={router} />
    </>
  );
}

export default App;
