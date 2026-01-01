import { createFileRoute, Outlet } from '@tanstack/react-router';

import { RouteError } from '@/components/errors';

/**
 * Layout route for /project/screenplay/*
 * This provides a pass-through layout that renders child routes via Outlet.
 * Required for TanStack Router's file-based routing to properly render
 * child routes like /project/screenplay/configure.
 */
export const Route = createFileRoute('/project/screenplay')({
  component: ScreenplayLayout,
  errorComponent: RouteError,
});

function ScreenplayLayout() {
  return <Outlet />;
}
