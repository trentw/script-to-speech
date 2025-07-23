import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

import { render, screen } from '@/test/utils/render';

import { Button } from '../button';

describe('Button Component', () => {
  describe('Accessibility', () => {
    // TODO: Enable this test when canvas issue is resolved
    // The test fails with: "Error: Not implemented: HTMLCanvasElement.prototype.getContext"
    // This is a known issue with jsdom and axe-core's color contrast checking
    // Options: 1) Install canvas package with native deps, 2) Use browser mode, 3) Mock canvas
    it.skip('should not have accessibility violations', async () => {
      // Arrange
      const { container } = render(<Button>Click me</Button>);

      // Act
      const results = await axe(container);

      // Assert
      expect(results).toHaveNoViolations();
    });

    it('should support aria-label', async () => {
      // Arrange
      render(<Button aria-label="Submit form">Submit</Button>);

      // Assert - Just check aria-label without axe
      expect(screen.getByLabelText('Submit form')).toBeInTheDocument();
    });

    it('should be keyboard navigable', async () => {
      // Arrange
      const user = userEvent.setup();
      render(
        <>
          <input type="text" />
          <Button>Focus me</Button>
        </>
      );
      const button = screen.getByRole('button', { name: 'Focus me' });

      // Act
      await user.tab();
      await user.tab();

      // Assert
      expect(button).toHaveFocus();
    });
  });

  describe('Click Events', () => {
    it('should handle click events', async () => {
      // Arrange
      const user = userEvent.setup();
      const handleClick = vi.fn();
      render(<Button onClick={handleClick}>Click me</Button>);
      const button = screen.getByRole('button', { name: 'Click me' });

      // Act
      await user.click(button);

      // Assert
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should handle keyboard activation', async () => {
      // Arrange
      const user = userEvent.setup();
      const handleClick = vi.fn();
      render(<Button onClick={handleClick}>Press me</Button>);
      const button = screen.getByRole('button', { name: 'Press me' });

      // Act
      button.focus();
      await user.keyboard('{Enter}');

      // Assert
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('should handle space key activation', async () => {
      // Arrange
      const user = userEvent.setup();
      const handleClick = vi.fn();
      render(<Button onClick={handleClick}>Press me</Button>);
      const button = screen.getByRole('button', { name: 'Press me' });

      // Act
      button.focus();
      await user.keyboard(' ');

      // Assert
      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });

  describe('Variants', () => {
    it('should render default variant', () => {
      // Arrange & Act
      render(<Button>Default</Button>);
      const button = screen.getByRole('button', { name: 'Default' });

      // Assert
      expect(button).toHaveClass('bg-primary');
      expect(button).toHaveClass('text-primary-foreground');
    });

    it('should render destructive variant', () => {
      // Arrange & Act
      render(<Button variant="destructive">Delete</Button>);
      const button = screen.getByRole('button', { name: 'Delete' });

      // Assert
      expect(button).toHaveClass('bg-destructive');
      expect(button).toHaveClass('text-white');
    });

    it('should render outline variant', () => {
      // Arrange & Act
      render(<Button variant="outline">Outline</Button>);
      const button = screen.getByRole('button', { name: 'Outline' });

      // Assert
      expect(button).toHaveClass('border');
      expect(button).toHaveClass('bg-background');
    });

    it('should render secondary variant', () => {
      // Arrange & Act
      render(<Button variant="secondary">Secondary</Button>);
      const button = screen.getByRole('button', { name: 'Secondary' });

      // Assert
      expect(button).toHaveClass('bg-secondary');
      expect(button).toHaveClass('text-secondary-foreground');
    });

    it('should render ghost variant', () => {
      // Arrange & Act
      render(<Button variant="ghost">Ghost</Button>);
      const button = screen.getByRole('button', { name: 'Ghost' });

      // Assert
      expect(button).toHaveClass('hover:bg-accent');
      expect(button).toHaveClass('hover:text-accent-foreground');
    });

    it('should render link variant', () => {
      // Arrange & Act
      render(<Button variant="link">Link</Button>);
      const button = screen.getByRole('button', { name: 'Link' });

      // Assert
      expect(button).toHaveClass('text-primary');
      expect(button).toHaveClass('underline-offset-4');
    });
  });

  describe('Disabled State', () => {
    it('should not fire click events when disabled', async () => {
      // Arrange
      const user = userEvent.setup();
      const handleClick = vi.fn();
      render(
        <Button disabled onClick={handleClick}>
          Disabled button
        </Button>
      );
      const button = screen.getByRole('button', { name: 'Disabled button' });

      // Act
      await user.click(button);

      // Assert
      expect(handleClick).not.toHaveBeenCalled();
      expect(button).toBeDisabled();
    });

    it('should have proper disabled styling', () => {
      // Arrange & Act
      render(<Button disabled>Disabled</Button>);
      const button = screen.getByRole('button', { name: 'Disabled' });

      // Assert
      expect(button).toHaveClass('disabled:pointer-events-none');
      expect(button).toHaveClass('disabled:opacity-50');
    });

    it('should have accessibility attributes when disabled', () => {
      // Arrange
      render(<Button disabled>Disabled button</Button>);

      // Assert - Check attributes without axe
      const button = screen.getByRole('button', { name: 'Disabled button' });
      expect(button).toBeDisabled();
      expect(button).toHaveAttribute('disabled');
    });
  });

  describe('Size Props', () => {
    it('should render different sizes', () => {
      // Arrange & Act
      const { rerender } = render(<Button size="sm">Small</Button>);
      const smallButton = screen.getByRole('button', { name: 'Small' });

      // Assert small - size sm: h-8 px-3
      expect(smallButton).toHaveClass('h-8');
      expect(smallButton).toHaveClass('px-3');

      // Act - rerender with default size
      rerender(<Button>Default</Button>);
      const defaultButton = screen.getByRole('button', { name: 'Default' });

      // Assert default - size default: h-9 px-4
      expect(defaultButton).toHaveClass('h-9');
      expect(defaultButton).toHaveClass('px-4');

      // Act - rerender with large size
      rerender(<Button size="lg">Large</Button>);
      const largeButton = screen.getByRole('button', { name: 'Large' });

      // Assert large - size lg: h-10 px-6
      expect(largeButton).toHaveClass('h-10');
      expect(largeButton).toHaveClass('px-6');
    });
  });

  describe('As Child Prop', () => {
    it('should render as a different element when asChild is true', () => {
      // Arrange & Act
      render(
        <Button asChild>
          <a href="/test">Link Button</a>
        </Button>
      );

      // Assert
      const link = screen.getByRole('link', { name: 'Link Button' });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', '/test');
      // Should have button styles applied
      expect(link).toHaveClass('inline-flex');
      expect(link).toHaveClass('items-center');
    });
  });
});
