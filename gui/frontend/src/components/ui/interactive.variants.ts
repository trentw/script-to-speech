import { cva } from 'class-variance-authority';

/**
 * Centralized interactive states for UI components
 * Provides consistent hover and interaction patterns across the application
 */

// Interactive card variants for list items and selection cards
export const interactiveCardVariants = cva('transition-colors cursor-pointer', {
  variants: {
    variant: {
      // Standard hover state for cards in lists
      default: 'hover:bg-accent/50',
      // More subtle hover for already selected items
      subtle: 'hover:bg-muted/80',
      // Selection cards with border change
      selection: 'hover:bg-accent hover:border-primary/20',
      // For cards that navigate or perform actions
      action: 'hover:bg-accent hover:shadow-md',
    },
    state: {
      // When a card is selected/active
      selected: 'border-primary bg-accent',
      // Normal unselected state
      idle: '',
    },
  },
  defaultVariants: {
    variant: 'default',
    state: 'idle',
  },
});

// Tab trigger affordances
export const tabTriggerVariants = {
  base: 'cursor-pointer transition-colors',
  hover: 'hover:bg-muted/80',
  // Full class string for direct use
  full: 'cursor-pointer transition-colors hover:bg-muted/80',
};

// File upload zone variants
export const fileUploadZoneVariants = cva(
  'relative rounded-lg border-2 border-dashed p-8 text-center transition-all',
  {
    variants: {
      state: {
        idle: 'border-muted-foreground/25 hover:border-primary/50 hover:bg-primary/5 cursor-pointer',
        active: 'border-primary bg-primary/5',
        disabled: 'cursor-not-allowed opacity-50 pointer-events-none',
        hasFile:
          'bg-muted/50 border-muted-foreground/40 cursor-pointer hover:bg-muted/60',
      },
    },
    defaultVariants: {
      state: 'idle',
    },
  }
);

// Navigation item variants (for both expanded and collapsed states)
export const navigationItemVariants = {
  base: 'flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors',
  hover: 'hover:bg-accent hover:text-accent-foreground',
  active: 'bg-primary text-primary-foreground hover:bg-primary/90',
  collapsed: 'px-2', // Reduced padding when sidebar is collapsed
};

// Utility classes for common interactive patterns
export const interactiveUtils = {
  // Focus ring for keyboard navigation
  focusRing:
    'focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
  // Smooth transitions
  transition: 'transition-all duration-200',
  // Disabled state
  disabled: 'disabled:pointer-events-none disabled:opacity-50',
  // Clickable area
  clickable: 'cursor-pointer select-none',
};
