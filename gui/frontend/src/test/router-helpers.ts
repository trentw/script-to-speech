/**
 * Test utilities for TanStack Router and Playwright
 */

import { expect, Page } from '@playwright/test';
import type { QueryClient } from '@tanstack/react-query';
import type { Router } from '@tanstack/react-router';
import { createMemoryHistory } from '@tanstack/react-router';

import { createScreenplayTaskRoute, ROUTES } from '../lib/routes';
import { createAppRouter, type RouterContext } from '../router';

// Mock router utilities for unit tests
export function createMockRouter(
  initialPath: string = '/',
  queryClient?: QueryClient
): Router<RouterContext['routeTree'], RouterContext> {
  const memoryHistory = createMemoryHistory({
    initialEntries: [initialPath],
  });

  // Create a mock query client if not provided
  const mockQueryClient =
    queryClient ||
    ({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    } as unknown as QueryClient);

  // Create router with memory history for tests
  const router = createAppRouter(mockQueryClient);
  // @ts-expect-error - Replacing history for testing
  router.history = memoryHistory;

  return router;
}

// Playwright navigation helpers
export class PlaywrightNavigator {
  constructor(private page: Page) {}

  /**
   * Navigate to a route and wait for it to load
   */
  async navigateTo(path: string): Promise<void> {
    await this.page.goto(`#${path}`);
    await this.waitForRouteLoad();
  }

  /**
   * Navigate to TTS page
   */
  async navigateToTTS(): Promise<void> {
    await this.navigateTo(ROUTES.TTS);
  }

  /**
   * Navigate to Screenplay page
   */
  async navigateToScreenplay(): Promise<void> {
    await this.navigateTo(ROUTES.SCREENPLAY.ROOT);
  }

  /**
   * Navigate to Screenplay task page
   */
  async navigateToScreenplayTask(taskId: string): Promise<void> {
    await this.navigateTo(createScreenplayTaskRoute(taskId));
  }

  /**
   * Click a navigation link and wait for navigation
   */
  async clickNavLink(linkText: string): Promise<void> {
    await this.page.getByRole('link', { name: linkText }).click();
    await this.waitForRouteLoad();
  }

  /**
   * Wait for route to fully load
   */
  async waitForRouteLoad(): Promise<void> {
    // Wait for any loading indicators to disappear
    await this.page.waitForLoadState('networkidle');

    // Wait for common loading states to be gone
    const loadingSelectors = [
      '[data-testid="app-loading"]',
      '[data-testid="route-loading"]',
      '.loading-spinner',
      '[aria-busy="true"]',
    ];

    for (const selector of loadingSelectors) {
      const element = this.page.locator(selector);
      if ((await element.count()) > 0) {
        await element.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {
          // Ignore timeout, element might not exist
        });
      }
    }
  }

  /**
   * Get current route path
   */
  async getCurrentPath(): Promise<string> {
    const url = new URL(this.page.url());
    return url.hash.slice(1) || '/';
  }

  /**
   * Assert current route
   */
  async assertCurrentRoute(expectedPath: string): Promise<void> {
    const currentPath = await this.getCurrentPath();
    expect(currentPath).toBe(expectedPath);
  }

  /**
   * Wait for navigation to complete
   */
  async waitForNavigation(path: string): Promise<void> {
    await this.page.waitForURL(`**/#${path}`);
    await this.waitForRouteLoad();
  }
}

// Route testing utilities
export const routeTestUtils = {
  /**
   * Get all testable routes (excluding parameterized routes)
   */
  getTestableRoutes(): string[] {
    return [ROUTES.HOME, ROUTES.TTS, ROUTES.SCREENPLAY.ROOT];
  },

  /**
   * Get parameterized test routes with example params
   */
  getParameterizedTestRoutes(): Array<{
    path: string;
    params: Record<string, string>;
  }> {
    return [
      {
        path: ROUTES.SCREENPLAY.TASK,
        params: { taskId: 'test-task-123' },
      },
    ];
  },

  /**
   * Create a test route with params
   */
  createTestRoute(template: string, params: Record<string, string>): string {
    let path = template;
    Object.entries(params).forEach(([key, value]) => {
      path = path.replace(`$${key}`, value);
    });
    return path;
  },
};

// Mock navigation context for testing components
export function createMockNavigationContext() {
  const navigateMock = jest.fn();
  const context = {
    navigate: navigateMock,
    back: jest.fn(),
    forward: jest.fn(),
    canGoBack: jest.fn(() => true),
    canGoForward: jest.fn(() => false),
  };

  return {
    context,
    navigateMock,
    resetMocks: () => {
      Object.values(context).forEach((fn) => {
        if (typeof fn === 'function' && 'mockReset' in fn) {
          (fn as jest.Mock).mockReset();
        }
      });
    },
  };
}

// Assertion helpers for Playwright
export const routeAssertions = {
  /**
   * Assert navigation item is active
   */
  async assertNavItemActive(page: Page, label: string): Promise<void> {
    const navItem = page.getByRole('link', { name: label });
    await expect(navItem).toHaveAttribute('aria-current', 'page');
  },

  /**
   * Assert breadcrumb navigation
   */
  async assertBreadcrumbs(page: Page, expectedCrumbs: string[]): Promise<void> {
    const breadcrumbs = page.locator(
      '[data-testid="breadcrumbs"] a, [data-testid="breadcrumbs"] span'
    );
    const texts = await breadcrumbs.allTextContents();
    expect(texts).toEqual(expectedCrumbs);
  },

  /**
   * Assert route title
   */
  async assertRouteTitle(page: Page, expectedTitle: string): Promise<void> {
    await expect(
      page.locator('h1, [data-testid="page-title"]').first()
    ).toHaveText(expectedTitle);
  },
};

// History mock for testing navigation guards
export function createMockHistory() {
  const entries: string[] = ['/'];
  let currentIndex = 0;

  return {
    push: jest.fn((path: string) => {
      entries.splice(currentIndex + 1);
      entries.push(path);
      currentIndex++;
    }),

    replace: jest.fn((path: string) => {
      entries[currentIndex] = path;
    }),

    back: jest.fn(() => {
      if (currentIndex > 0) currentIndex--;
    }),

    forward: jest.fn(() => {
      if (currentIndex < entries.length - 1) currentIndex++;
    }),

    get current() {
      return entries[currentIndex];
    },

    get entries() {
      return [...entries];
    },

    reset: () => {
      entries.length = 0;
      entries.push('/');
      currentIndex = 0;
    },
  };
}

// Test data factories
export const routeTestData = {
  /**
   * Create test task ID
   */
  createTestTaskId: (prefix: string = 'test'): string => {
    return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  },

  /**
   * Create test route params
   */
  createTestRouteParams: (
    overrides?: Partial<Record<string, string>>
  ): Record<string, string> => {
    return {
      taskId: routeTestData.createTestTaskId(),
      ...overrides,
    };
  },
};

// Playwright route interception helpers
export class RouteInterceptor {
  constructor(private page: Page) {}

  /**
   * Intercept navigation and return the attempted path
   */
  async interceptNavigation(): Promise<{ path: string; prevented: boolean }> {
    let interceptedPath = '';
    let prevented = false;

    await this.page.evaluate(() => {
      const originalPushState = window.history.pushState;
      window.history.pushState = function (...args) {
        window.dispatchEvent(
          new CustomEvent('navigation-intercepted', {
            detail: { path: args[2], prevented: false },
          })
        );
        return originalPushState.apply(this, args);
      };
    });

    return new Promise((resolve) => {
      this.page.once('navigation-intercepted', (event: unknown) => {
        interceptedPath = event.detail.path;
        prevented = event.detail.prevented;
        resolve({ path: interceptedPath, prevented });
      });
    });
  }

  /**
   * Block navigation to specific routes
   */
  async blockNavigationTo(blockedPaths: string[]): Promise<void> {
    await this.page.evaluate((paths) => {
      const originalPushState = window.history.pushState;
      window.history.pushState = function (...args) {
        const path = args[2] as string;
        if (paths.some((blocked) => path.includes(blocked))) {
          window.dispatchEvent(
            new CustomEvent('navigation-blocked', {
              detail: { path },
            })
          );
          return;
        }
        return originalPushState.apply(this, args);
      };
    }, blockedPaths);
  }
}
