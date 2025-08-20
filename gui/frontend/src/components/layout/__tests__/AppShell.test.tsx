import { beforeEach, describe, expect, it, vi } from 'vitest';

import { render, screen } from '@/test/utils/render';

import { AppShell } from '../AppShell';

describe('AppShell', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render main content', () => {
      // Arrange & Act
      render(
        <AppShell main={<div data-testid="main-content">Main Content</div>} />
      );

      // Assert
      expect(screen.getByTestId('main-content')).toBeInTheDocument();
      expect(screen.getByText('Main Content')).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      // Arrange & Act
      const { container } = render(
        <AppShell main={<div>Main</div>} className="custom-class" />
      );

      // Assert
      const appShell = container.querySelector('.app-shell');
      expect(appShell).toHaveClass('custom-class');
    });
  });

  describe('Layout Areas', () => {
    it('should render all layout areas when provided', () => {
      // Arrange & Act
      render(
        <AppShell
          navigation={<div data-testid="nav">Navigation</div>}
          header={<div data-testid="header">Header</div>}
          main={<div data-testid="main">Main</div>}
          panel={<div data-testid="panel">Panel</div>}
          footer={<div data-testid="footer">Footer</div>}
        />
      );

      // Assert
      expect(screen.getByTestId('nav')).toBeInTheDocument();
      expect(screen.getByTestId('header')).toBeInTheDocument();
      expect(screen.getByTestId('main')).toBeInTheDocument();
      expect(screen.getByTestId('panel')).toBeInTheDocument();
      expect(screen.getByTestId('footer')).toBeInTheDocument();
    });

    it('should only render provided areas', () => {
      // Arrange & Act
      render(
        <AppShell
          main={<div data-testid="main">Main</div>}
          header={<div data-testid="header">Header</div>}
        />
      );

      // Assert
      expect(screen.getByTestId('main')).toBeInTheDocument();
      expect(screen.getByTestId('header')).toBeInTheDocument();
      expect(screen.queryByTestId('nav')).not.toBeInTheDocument();
      expect(screen.queryByTestId('panel')).not.toBeInTheDocument();
      expect(screen.queryByTestId('footer')).not.toBeInTheDocument();
    });
  });

  describe('CSS Classes', () => {
    it('should apply has-nav class when navigation is provided', () => {
      // Arrange & Act
      const { container } = render(
        <AppShell navigation={<div>Nav</div>} main={<div>Main</div>} />
      );

      // Assert
      const appShell = container.querySelector('.app-shell');
      expect(appShell).toHaveClass('has-nav');
      expect(appShell).not.toHaveClass('has-panel');
    });

    it('should apply has-panel class when panel is provided', () => {
      // Arrange & Act
      const { container } = render(
        <AppShell panel={<div>Panel</div>} main={<div>Main</div>} />
      );

      // Assert
      const appShell = container.querySelector('.app-shell');
      expect(appShell).toHaveClass('has-panel');
      expect(appShell).not.toHaveClass('has-nav');
    });

    it('should apply both has-nav and has-panel classes', () => {
      // Arrange & Act
      const { container } = render(
        <AppShell
          navigation={<div>Nav</div>}
          panel={<div>Panel</div>}
          main={<div>Main</div>}
        />
      );

      // Assert
      const appShell = container.querySelector('.app-shell');
      expect(appShell).toHaveClass('has-nav');
      expect(appShell).toHaveClass('has-panel');
    });
  });

  describe('Grid Area Classes', () => {
    it('should apply correct grid area classes', () => {
      // Arrange & Act
      const { container } = render(
        <AppShell
          navigation={<div>Nav</div>}
          header={<div>Header</div>}
          main={<div>Main</div>}
          panel={<div>Panel</div>}
          footer={<div>Footer</div>}
        />
      );

      // Assert
      expect(container.querySelector('.grid-area-nav')).toBeInTheDocument();
      expect(container.querySelector('.grid-area-header')).toBeInTheDocument();
      expect(container.querySelector('.grid-area-main')).toBeInTheDocument();
      expect(container.querySelector('.grid-area-panel')).toBeInTheDocument();
      expect(container.querySelector('.grid-area-footer')).toBeInTheDocument();
    });
  });

  describe('Panel Behavior', () => {
    it('should render panel when provided', () => {
      // Arrange & Act
      const { container } = render(
        <AppShell main={<div>Main</div>} panel={<div>Panel Content</div>} />
      );

      // Assert
      const panel = container.querySelector('.grid-area-panel');
      expect(panel).toBeInTheDocument();
      expect(panel).toHaveTextContent('Panel Content');
    });

    it('should not render panel when not provided', () => {
      // Arrange & Act
      const { container } = render(<AppShell main={<div>Main</div>} />);

      // Assert
      const panel = container.querySelector('.grid-area-panel');
      expect(panel).not.toBeInTheDocument();
    });
  });

  describe('Responsive Behavior', () => {
    it('should maintain structure at different viewport sizes', () => {
      // Arrange & Act
      const { container } = render(
        <AppShell
          navigation={<div>Nav</div>}
          main={<div>Main</div>}
          panel={<div>Panel</div>}
        />
      );

      // Assert - Structure should remain the same, CSS handles responsiveness
      const appShell = container.querySelector('.app-shell');
      expect(appShell).toHaveClass('has-nav');
      expect(appShell).toHaveClass('has-panel');
    });

    it('should apply container query styles', () => {
      // Arrange & Act
      const { container } = render(<AppShell main={<div>Main</div>} />);

      // Assert - Container should be set up for container queries
      const appShell = container.querySelector('.app-shell');
      expect(appShell).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should maintain proper ARIA landmarks', () => {
      // Arrange & Act
      const { container } = render(
        <AppShell
          navigation={<nav aria-label="Main navigation">Navigation</nav>}
          header={<div>Header</div>}
          main={<div>Main Content</div>}
          footer={<div>Footer</div>}
        />
      );

      // Assert
      expect(screen.getByRole('navigation')).toBeInTheDocument();

      // Check that all grid areas exist with proper classes
      const mainArea = container.querySelector('.grid-area-main');
      const header = container.querySelector('.grid-area-header');
      const footer = container.querySelector('.grid-area-footer');

      expect(mainArea).toBeInTheDocument();
      expect(header).toBeInTheDocument();
      expect(footer).toBeInTheDocument();
    });

    it('should support semantic HTML elements', () => {
      // Arrange & Act
      const { container } = render(
        <AppShell
          navigation={<nav>Nav</nav>}
          header={<header>Header</header>}
          main={<main>Main</main>}
          footer={<footer>Footer</footer>}
        />
      );

      // Assert
      expect(container.querySelector('nav')).toBeInTheDocument();
      expect(container.querySelector('header')).toBeInTheDocument();
      expect(container.querySelector('main')).toBeInTheDocument();
      expect(container.querySelector('footer')).toBeInTheDocument();
    });

    it('should handle focus management properly', () => {
      // Arrange & Act
      render(
        <AppShell
          navigation={
            <nav>
              <button>Nav Button</button>
            </nav>
          }
          main={
            <main>
              <button>Main Button</button>
            </main>
          }
        />
      );

      // Assert
      const navButton = screen.getByText('Nav Button');
      const mainButton = screen.getByText('Main Button');

      expect(navButton).toBeInTheDocument();
      expect(mainButton).toBeInTheDocument();

      // Both buttons should be focusable
      navButton.focus();
      expect(document.activeElement).toBe(navButton);

      mainButton.focus();
      expect(document.activeElement).toBe(mainButton);
    });
  });

  describe('Border Styles', () => {
    it('should apply correct border classes to layout areas', () => {
      // Arrange & Act
      const { container } = render(
        <AppShell
          navigation={<div>Nav</div>}
          header={<div>Header</div>}
          main={<div>Main</div>}
          panel={<div>Panel</div>}
          footer={<div>Footer</div>}
        />
      );

      // Assert
      const nav = container.querySelector('.grid-area-nav');
      const header = container.querySelector('.grid-area-header');
      const panel = container.querySelector('.grid-area-panel');
      const footer = container.querySelector('.grid-area-footer');

      expect(nav).toHaveClass('border-r');
      expect(header).toHaveClass('border-b');
      expect(panel).toHaveClass('border-l');
      expect(footer).toHaveClass('border-t');
    });
  });

  describe('Background Colors', () => {
    it('should apply correct background classes', () => {
      // Arrange & Act
      const { container } = render(
        <AppShell
          navigation={<div>Nav</div>}
          header={<div>Header</div>}
          main={<div>Main</div>}
          panel={<div>Panel</div>}
          footer={<div>Footer</div>}
        />
      );

      // Assert
      const nav = container.querySelector('.grid-area-nav');
      const header = container.querySelector('.grid-area-header');
      const panel = container.querySelector('.grid-area-panel');
      const footer = container.querySelector('.grid-area-footer');

      expect(nav).toHaveClass('bg-background');
      expect(header).toHaveClass('bg-background');
      expect(panel).toHaveClass('bg-muted/30');
      expect(footer).toHaveClass('bg-background');
    });
  });

  describe('Integration with Children', () => {
    it('should properly render complex children', () => {
      // Arrange
      const NavigationComponent = () => (
        <nav>
          <ul>
            <li>Item 1</li>
            <li>Item 2</li>
          </ul>
        </nav>
      );

      const MainComponent = () => (
        <div>
          <h1>Title</h1>
          <p>Content</p>
        </div>
      );

      // Act
      render(
        <AppShell
          navigation={<NavigationComponent />}
          main={<MainComponent />}
        />
      );

      // Assert
      expect(screen.getByText('Item 1')).toBeInTheDocument();
      expect(screen.getByText('Item 2')).toBeInTheDocument();
      expect(screen.getByText('Title')).toBeInTheDocument();
      expect(screen.getByText('Content')).toBeInTheDocument();
    });
  });
});
