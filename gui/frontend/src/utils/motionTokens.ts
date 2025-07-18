/**
 * Centralized motion and animation configuration tokens
 * 
 * This file provides consistent animation timing, easing, and stagger values
 * across the application to maintain design consistency and eliminate
 * scattered "magic numbers" that violate DRY principles.
 */

// Duration tokens for different types of animations
export const duration = {
  /** Fast animations (120ms) - for quick state changes */
  fast: 0.12,
  /** Moderate animations (200ms) - for standard transitions */
  moderate: 0.2,
  /** Slow animations (300ms) - for complex layout changes */
  slow: 0.3,
  /** Instant (0ms) - for immediate state changes */
  instant: 0
} as const

// Stagger timing for coordinated animations
export const stagger = {
  /** Sidebar animation delay (100ms) - for responsive layout changes */
  sidebar: 0.1,
  /** Panel animation delay (150ms) - for panel show/hide transitions */
  panel: 0.15,
  /** Content animation delay (50ms) - for content transitions */
  content: 0.05
} as const

// Spring physics configuration for Framer Motion
export const springs = {
  /** Standard spring - balanced feel for most UI animations */
  standard: {
    type: "spring" as const,
    damping: 30,
    stiffness: 200
  },
  /** Gentle spring - softer feel for large layout changes */
  gentle: {
    type: "spring" as const,
    damping: 40,
    stiffness: 150
  },
  /** Snappy spring - quick, responsive feel for small interactions */
  snappy: {
    type: "spring" as const,
    damping: 25,
    stiffness: 300
  }
} as const

// Opacity transition configuration
export const opacity = {
  /** Standard opacity transition */
  standard: {
    duration: duration.moderate
  },
  /** Fast opacity transition */
  fast: {
    duration: duration.fast
  }
} as const

// Combined motion tokens for common use cases
export const motionTokens = {
  /** Responsive sidebar animation */
  responsiveSidebar: {
    stagger: stagger.sidebar,
    spring: springs.standard,
    opacity: opacity.standard
  },
  /** Panel show/hide animation */
  panelTransition: {
    stagger: stagger.panel,
    spring: springs.standard,
    opacity: opacity.standard
  },
  /** Content fade animation */
  contentFade: {
    stagger: stagger.content,
    spring: springs.gentle,
    opacity: opacity.fast
  }
} as const

// Type exports for better TypeScript support
export type Duration = typeof duration
export type Stagger = typeof stagger
export type Springs = typeof springs
export type MotionTokens = typeof motionTokens