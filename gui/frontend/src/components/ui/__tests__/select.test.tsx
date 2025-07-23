import { describe, expect, it, vi } from 'vitest';

import { render, screen } from '@/test/utils/render';

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from '../select';

describe('Select Component', () => {
  describe('Basic Rendering', () => {
    it('should render with placeholder', () => {
      // Arrange & Act
      render(
        <Select>
          <SelectTrigger>
            <SelectValue placeholder="Select an option" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="option1">Option 1</SelectItem>
            <SelectItem value="option2">Option 2</SelectItem>
          </SelectContent>
        </Select>
      );

      // Assert
      expect(screen.getByText('Select an option')).toBeInTheDocument();
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('should display selected value', () => {
      // Arrange & Act
      render(
        <Select value="option2">
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="option1">Option 1</SelectItem>
            <SelectItem value="option2">Option 2</SelectItem>
          </SelectContent>
        </Select>
      );

      // Assert
      expect(screen.getByRole('combobox')).toHaveTextContent('Option 2');
    });

    it('should handle controlled value changes', () => {
      // Arrange
      const handleChange = vi.fn();
      const { rerender } = render(
        <Select value="option1" onValueChange={handleChange}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="option1">Option 1</SelectItem>
            <SelectItem value="option2">Option 2</SelectItem>
          </SelectContent>
        </Select>
      );

      // Assert initial value
      expect(screen.getByRole('combobox')).toHaveTextContent('Option 1');

      // Act - update value
      rerender(
        <Select value="option2" onValueChange={handleChange}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="option1">Option 1</SelectItem>
            <SelectItem value="option2">Option 2</SelectItem>
          </SelectContent>
        </Select>
      );

      // Assert updated value
      expect(screen.getByRole('combobox')).toHaveTextContent('Option 2');
    });
  });

  describe('Trigger Behavior', () => {
    it('should render trigger with correct attributes', () => {
      // Arrange & Act
      render(
        <Select>
          <SelectTrigger aria-label="Select a fruit">
            <SelectValue placeholder="Choose..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="apple">Apple</SelectItem>
          </SelectContent>
        </Select>
      );

      // Assert
      const trigger = screen.getByRole('combobox');
      expect(trigger).toHaveAttribute('aria-label', 'Select a fruit');
      expect(trigger).toHaveAttribute('aria-expanded', 'false');
      expect(trigger).toHaveAttribute('type', 'button');
      expect(trigger).toHaveAttribute('data-state', 'closed');
    });

    it('should show chevron icon', () => {
      // Arrange & Act
      render(
        <Select>
          <SelectTrigger>
            <SelectValue placeholder="Select" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="item">Item</SelectItem>
          </SelectContent>
        </Select>
      );

      // Assert
      const chevron = screen.getByRole('combobox').querySelector('svg');
      expect(chevron).toBeInTheDocument();
      expect(chevron).toHaveClass('lucide-chevron-down');
    });
  });

  describe('Disabled State', () => {
    it('should handle disabled state', () => {
      // Arrange & Act
      render(
        <Select disabled>
          <SelectTrigger>
            <SelectValue placeholder="Disabled select" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="option1">Option 1</SelectItem>
          </SelectContent>
        </Select>
      );

      // Assert
      const trigger = screen.getByRole('combobox');
      expect(trigger).toHaveAttribute('data-disabled');
      expect(trigger).toHaveClass('disabled:cursor-not-allowed');
      expect(trigger).toHaveClass('disabled:opacity-50');
    });
  });

  describe('Sizes', () => {
    it('should render different sizes', () => {
      // Arrange & Act
      const { rerender } = render(
        <Select>
          <SelectTrigger size="sm">
            <SelectValue placeholder="Small" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="option1">Option 1</SelectItem>
          </SelectContent>
        </Select>
      );

      // Assert small
      expect(screen.getByRole('combobox')).toHaveAttribute('data-size', 'sm');

      // Act - rerender with default size
      rerender(
        <Select>
          <SelectTrigger>
            <SelectValue placeholder="Default" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="option1">Option 1</SelectItem>
          </SelectContent>
        </Select>
      );

      // Assert default
      expect(screen.getByRole('combobox')).toHaveAttribute(
        'data-size',
        'default'
      );
    });
  });

  describe('Custom Classes', () => {
    it('should apply custom classes to trigger', () => {
      // Arrange & Act
      render(
        <Select>
          <SelectTrigger className="custom-trigger-class">
            <SelectValue placeholder="Custom" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="option1">Option 1</SelectItem>
          </SelectContent>
        </Select>
      );

      // Assert
      expect(screen.getByRole('combobox')).toHaveClass('custom-trigger-class');
    });
  });

  describe('Select Content Structure', () => {
    it('should render with groups and labels structure', () => {
      // Arrange & Act
      render(
        <Select>
          <SelectTrigger>
            <SelectValue placeholder="Select fruit" />
          </SelectTrigger>
          <SelectContent>
            <SelectGroup>
              <SelectLabel>Citrus</SelectLabel>
              <SelectItem value="orange">Orange</SelectItem>
              <SelectItem value="lemon">Lemon</SelectItem>
            </SelectGroup>
            <SelectSeparator />
            <SelectGroup>
              <SelectLabel>Berries</SelectLabel>
              <SelectItem value="strawberry">Strawberry</SelectItem>
            </SelectGroup>
          </SelectContent>
        </Select>
      );

      // Assert - check that trigger renders with correct attributes
      const trigger = screen.getByRole('combobox');
      expect(trigger).toBeInTheDocument();
      expect(trigger).toHaveAttribute('data-slot', 'select-trigger');
      expect(trigger).toHaveTextContent('Select fruit');
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA attributes', () => {
      // Arrange & Act
      render(
        <Select value="option1">
          <SelectTrigger aria-label="Fruit selection">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="option1">Option 1</SelectItem>
          </SelectContent>
        </Select>
      );

      // Assert
      const trigger = screen.getByRole('combobox');
      expect(trigger).toHaveAttribute('aria-label', 'Fruit selection');
      expect(trigger).toHaveAttribute('aria-expanded', 'false');
      expect(trigger).toHaveAttribute('role', 'combobox');
      expect(trigger).toHaveAttribute('aria-autocomplete', 'none');
    });

    it('should handle required state', () => {
      // Arrange & Act
      render(
        <Select required>
          <SelectTrigger>
            <SelectValue placeholder="Required field" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="option1">Option 1</SelectItem>
          </SelectContent>
        </Select>
      );

      // Assert
      const trigger = screen.getByRole('combobox');
      expect(trigger).toHaveAttribute('aria-required', 'true');
    });
  });
});
