import { cn } from './utils';

interface NavigationItemStyleOptions {
  isActive: boolean;
  isCollapsed?: boolean;
  isDisabled?: boolean;
}

/**
 * Returns the appropriate className for a navigation item based on its state
 */
export function getNavigationItemClassName({
  isActive,
  isCollapsed = false,
  isDisabled = false,
}: NavigationItemStyleOptions): string {
  return cn(
    'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-all',
    isCollapsed && 'justify-center px-2',
    isDisabled && 'opacity-50 cursor-not-allowed',
    isActive
      ? 'bg-gray-900 text-white shadow-sm'
      : 'text-gray-700 hover:bg-gray-100'
  );
}
