import type { LucideIcon } from 'lucide-react';

/**
 * Static metadata for routes that can be used for navigation,
 * UI configuration, and developer documentation.
 *
 * This interface demonstrates how routes can self-describe their
 * properties, eliminating the need for hardcoded logic throughout
 * the application.
 */
export interface RouteStaticData {
  /** Display title for headers and navigation (optional - can be inherited from parent) */
  title?: string;

  /** Icon component or identifier for navigation */
  icon?: LucideIcon | string;

  /** Brief description for developer documentation */
  description?: string;

  /** Navigation configuration */
  navigation?: {
    /** Label to show in navigation (defaults to title) */
    label?: string;
    /** Order in navigation menu */
    order?: number;
    /** Whether to show in main navigation */
    showInNav?: boolean;
  };

  /** UI feature flags */
  ui?: {
    /** Show side panel on desktop (TTS view) */
    showPanel?: boolean;
    /** Show footer */
    showFooter?: boolean;
    /** Mobile drawer options */
    mobileDrawers?: Array<'settings' | 'history'>;
  };

  /** Help text or additional documentation */
  helpText?: string;
}

// Example of extending for specific route needs:
// export interface DynamicRouteStaticData extends RouteStaticData {
//   getTitle?: (params: any) => string;
//   getBreadcrumb?: (params: any) => string;
// }
