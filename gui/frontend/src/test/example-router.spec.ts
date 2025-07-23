/**
 * Example Playwright test demonstrating router helper usage
 */

import { expect,test } from '@playwright/test';

import { createScreenplayTaskRoute,ROUTES } from '../lib/routes';
import { PlaywrightNavigator, routeAssertions, routeTestUtils } from './router-helpers';

test.describe('Navigation Example Tests', () => {
  let navigator: PlaywrightNavigator;
  
  test.beforeEach(async ({ page }) => {
    navigator = new PlaywrightNavigator(page);
    
    // Start at the home page
    await page.goto('/');
    await navigator.waitForRouteLoad();
  });
  
  test('should navigate between main routes', async ({ page }) => {
    // Navigate to TTS
    await navigator.navigateToTTS();
    await navigator.assertCurrentRoute(ROUTES.TTS);
    await routeAssertions.assertNavItemActive(page, 'Text to Speech');
    
    // Navigate to Screenplay
    await navigator.navigateToScreenplay();
    await navigator.assertCurrentRoute(ROUTES.SCREENPLAY.ROOT);
    await routeAssertions.assertNavItemActive(page, 'Screenplay Parser');
  });
  
  test('should navigate to screenplay task', async ({ page }) => {
    const taskId = routeTestUtils.createTestTaskId('test');
    
    // Navigate directly to a screenplay task
    await navigator.navigateToScreenplayTask(taskId);
    
    // Verify the route
    const expectedPath = createScreenplayTaskRoute(taskId);
    await navigator.assertCurrentRoute(expectedPath);
    
    // Check breadcrumbs
    await routeAssertions.assertBreadcrumbs(page, [
      'Home',
      'Screenplay Parser',
      'Task Details'
    ]);
  });
  
  test('should navigate using nav links', async ({ page }) => {
    // Click navigation links instead of programmatic navigation
    await navigator.clickNavLink('Text to Speech');
    await navigator.assertCurrentRoute(ROUTES.TTS);
    
    await navigator.clickNavLink('Screenplay Parser');
    await navigator.assertCurrentRoute(ROUTES.SCREENPLAY.ROOT);
  });
  
  test('should test all static routes', async () => {
    // Test all non-parameterized routes
    const routes = routeTestUtils.getTestableRoutes();
    
    for (const route of routes) {
      await navigator.navigateTo(route);
      await navigator.assertCurrentRoute(route);
    }
  });
  
  test('should test parameterized routes', async () => {
    // Test routes that require parameters
    const paramRoutes = routeTestUtils.getParameterizedTestRoutes();
    
    for (const { path, params } of paramRoutes) {
      const actualPath = routeTestUtils.createTestRoute(path, params);
      await navigator.navigateTo(actualPath);
      await navigator.assertCurrentRoute(actualPath);
    }
  });
  
  test('should handle navigation with loading states', async ({ page }) => {
    // Navigate and ensure loading states are handled
    await navigator.navigateToScreenplay();
    
    // Verify no loading indicators are visible
    await expect(page.locator('[data-testid="app-loading"]')).not.toBeVisible();
    await expect(page.locator('[aria-busy="true"]')).not.toBeVisible();
  });
  
  test('should get current path correctly', async () => {
    await navigator.navigateToTTS();
    const currentPath = await navigator.getCurrentPath();
    expect(currentPath).toBe(ROUTES.TTS);
  });
});

test.describe('Advanced Navigation Tests', () => {
  test('should wait for navigation to complete', async ({ page }) => {
    const navigator = new PlaywrightNavigator(page);
    await page.goto('/');
    
    // Start navigation and wait for it
    const navigationPromise = navigator.waitForNavigation(ROUTES.SCREENPLAY.ROOT);
    
    // Trigger navigation (e.g., via button click)
    await page.getByRole('link', { name: 'Screenplay Parser' }).click();
    
    // Wait for navigation to complete
    await navigationPromise;
    
    // Verify we're on the correct route
    await navigator.assertCurrentRoute(ROUTES.SCREENPLAY.ROOT);
  });
  
  test('should handle route with special characters in task ID', async ({ page }) => {
    const navigator = new PlaywrightNavigator(page);
    const specialTaskId = 'task-with-special_chars.123';
    
    await navigator.navigateToScreenplayTask(specialTaskId);
    
    const expectedPath = createScreenplayTaskRoute(specialTaskId);
    await navigator.assertCurrentRoute(expectedPath);
  });
});

// Example of testing route guards or navigation blocking
test.describe('Navigation Guard Tests', () => {
  test('should handle blocked navigation', async ({ page }) => {
    // This would be used with actual navigation guard implementation
    // Example showing the pattern
    
    await page.goto('/');
    
    // Mock a scenario where navigation is blocked
    await page.evaluate(() => {
      window.addEventListener('beforeunload', (e) => {
        e.preventDefault();
        e.returnValue = '';
      });
    });
    
    // Try to navigate away
    const dialog = page.waitForEvent('dialog');
    await page.getByRole('link', { name: 'Screenplay Parser' }).click();
    
    // Handle the confirmation dialog
    const confirmDialog = await dialog;
    expect(confirmDialog.type()).toBe('beforeunload');
    await confirmDialog.accept(); // or dismiss() to cancel
  });
});