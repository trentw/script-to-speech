import { describe, expect, it } from 'vitest';

import { render, screen } from '@/test/utils/render';

import { ResponsivePanel } from '../ResponsivePanel';

describe('ResponsivePanel', () => {
  describe('Basic Rendering', () => {
    it('should render children', () => {
      // Arrange & Act
      render(
        <ResponsivePanel>
          <div data-testid="child-content">Panel Content</div>
        </ResponsivePanel>
      );

      // Assert
      expect(screen.getByTestId('child-content')).toBeInTheDocument();
      expect(screen.getByText('Panel Content')).toBeInTheDocument();
    });

    it('should render title when provided', () => {
      // Arrange & Act
      render(
        <ResponsivePanel title="Settings Panel">
          <div>Content</div>
        </ResponsivePanel>
      );

      // Assert
      expect(screen.getByText('Settings Panel')).toBeInTheDocument();
      expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(
        'Settings Panel'
      );
    });

    it('should not render header when title is not provided', () => {
      // Arrange & Act
      const { container } = render(
        <ResponsivePanel>
          <div>Content</div>
        </ResponsivePanel>
      );

      // Assert
      expect(container.querySelector('header')).not.toBeInTheDocument();
      expect(screen.queryByRole('heading')).not.toBeInTheDocument();
    });
  });

  describe('CSS Classes', () => {
    it('should apply default classes', () => {
      // Arrange & Act
      const { container } = render(
        <ResponsivePanel>
          <div>Content</div>
        </ResponsivePanel>
      );

      // Assert
      const panel = container.querySelector('.responsive-panel');
      expect(panel).toBeInTheDocument();
      expect(panel).toHaveClass('flex', 'h-full', 'flex-col');
    });

    it('should apply custom className', () => {
      // Arrange & Act
      const { container } = render(
        <ResponsivePanel className="custom-class">
          <div>Content</div>
        </ResponsivePanel>
      );

      // Assert
      const panel = container.querySelector('.responsive-panel');
      expect(panel).toHaveClass('custom-class');
    });

    it('should apply panelClassName', () => {
      // Arrange & Act
      const { container } = render(
        <ResponsivePanel panelClassName="panel-custom-class">
          <div>Content</div>
        </ResponsivePanel>
      );

      // Assert
      const panel = container.querySelector('.responsive-panel');
      expect(panel).toHaveClass('panel-custom-class');
    });

    it('should apply both className and panelClassName', () => {
      // Arrange & Act
      const { container } = render(
        <ResponsivePanel
          className="custom-class"
          panelClassName="panel-custom-class"
        >
          <div>Content</div>
        </ResponsivePanel>
      );

      // Assert
      const panel = container.querySelector('.responsive-panel');
      expect(panel).toHaveClass('custom-class', 'panel-custom-class');
    });
  });

  describe('Container Queries', () => {
    it('should apply container query styles', () => {
      // Arrange & Act
      const { container } = render(
        <ResponsivePanel>
          <div>Content</div>
        </ResponsivePanel>
      );

      // Assert
      const panel = container.querySelector('.responsive-panel');
      expect(panel).toHaveStyle({
        containerType: 'inline-size',
        containerName: 'panel',
      });
    });
  });

  describe('Layout Structure', () => {
    it('should have proper flex layout structure', () => {
      // Arrange & Act
      const { container } = render(
        <ResponsivePanel title="Test Panel">
          <div>Content</div>
        </ResponsivePanel>
      );

      // Assert
      const panel = container.querySelector('.responsive-panel');
      const header = container.querySelector('header');
      const content = container.querySelector('.flex-1');

      expect(panel).toHaveClass('flex', 'h-full', 'flex-col');
      expect(header).toBeInTheDocument();
      expect(content).toHaveClass('overflow-y-auto');
    });

    it('should apply correct header styles when title is provided', () => {
      // Arrange & Act
      const { container } = render(
        <ResponsivePanel title="Test Panel">
          <div>Content</div>
        </ResponsivePanel>
      );

      // Assert
      const header = container.querySelector('header');
      expect(header).toHaveClass(
        'border-border',
        'flex',
        'items-center',
        'justify-between',
        'border-b',
        'p-4'
      );
    });

    it('should make content area scrollable', () => {
      // Arrange & Act
      const { container } = render(
        <ResponsivePanel>
          <div>Long content that might overflow</div>
        </ResponsivePanel>
      );

      // Assert
      const contentArea = container.querySelector('.flex-1');
      expect(contentArea).toHaveClass('overflow-y-auto');
    });
  });

  describe('Complex Children', () => {
    it('should render complex nested children', () => {
      // Arrange & Act
      render(
        <ResponsivePanel title="Complex Panel">
          <div>
            <h3>Section 1</h3>
            <ul>
              <li>Item 1</li>
              <li>Item 2</li>
            </ul>
            <h3>Section 2</h3>
            <p>Some paragraph content</p>
          </div>
        </ResponsivePanel>
      );

      // Assert
      expect(screen.getByText('Complex Panel')).toBeInTheDocument();
      expect(screen.getByText('Section 1')).toBeInTheDocument();
      expect(screen.getByText('Item 1')).toBeInTheDocument();
      expect(screen.getByText('Item 2')).toBeInTheDocument();
      expect(screen.getByText('Section 2')).toBeInTheDocument();
      expect(screen.getByText('Some paragraph content')).toBeInTheDocument();
    });

    it('should render React components as children', () => {
      // Arrange
      const ChildComponent = () => (
        <div data-testid="child-component">
          <button>Click me</button>
          <span>Status: Active</span>
        </div>
      );

      // Act
      render(
        <ResponsivePanel title="Component Panel">
          <ChildComponent />
        </ResponsivePanel>
      );

      // Assert
      expect(screen.getByTestId('child-component')).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: 'Click me' })
      ).toBeInTheDocument();
      expect(screen.getByText('Status: Active')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should use semantic heading element for title', () => {
      // Arrange & Act
      render(
        <ResponsivePanel title="Panel Title">
          <div>Content</div>
        </ResponsivePanel>
      );

      // Assert
      const heading = screen.getByRole('heading', { level: 2 });
      expect(heading).toHaveTextContent('Panel Title');
    });

    it('should support ARIA attributes', () => {
      // Arrange & Act
      const { container } = render(
        <ResponsivePanel title="Settings" className="settings-panel">
          <div>Settings content</div>
        </ResponsivePanel>
      );

      // Assert
      const panel = container.querySelector('.responsive-panel');
      expect(panel).toBeInTheDocument();

      // Can add aria attributes via className or children
      const heading = screen.getByRole('heading', { level: 2 });
      expect(heading).toHaveTextContent('Settings');
    });

    it('should maintain proper heading hierarchy', () => {
      // Arrange & Act
      render(
        <ResponsivePanel title="Main Panel">
          <div>
            <h3>Subsection 1</h3>
            <p>Content</p>
            <h3>Subsection 2</h3>
            <p>More content</p>
          </div>
        </ResponsivePanel>
      );

      // Assert
      const mainHeading = screen.getByRole('heading', { level: 2 });
      const subHeadings = screen.getAllByRole('heading', { level: 3 });

      expect(mainHeading).toHaveTextContent('Main Panel');
      expect(subHeadings).toHaveLength(2);
      expect(subHeadings[0]).toHaveTextContent('Subsection 1');
      expect(subHeadings[1]).toHaveTextContent('Subsection 2');
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty children', () => {
      // Arrange & Act
      const { container } = render(<ResponsivePanel title="Empty Panel" />);

      // Assert
      expect(screen.getByText('Empty Panel')).toBeInTheDocument();
      const contentArea = container.querySelector('.flex-1');
      expect(contentArea).toBeEmptyDOMElement();
    });

    it('should handle very long titles', () => {
      // Arrange
      const longTitle =
        'This is a very long title that might cause layout issues if not handled properly in the responsive panel component';

      // Act
      render(
        <ResponsivePanel title={longTitle}>
          <div>Content</div>
        </ResponsivePanel>
      );

      // Assert
      expect(screen.getByText(longTitle)).toBeInTheDocument();
    });

    it('should handle special characters in title', () => {
      // Arrange & Act
      render(
        <ResponsivePanel title="Panel & Settings <Test>">
          <div>Content</div>
        </ResponsivePanel>
      );

      // Assert
      expect(screen.getByText('Panel & Settings <Test>')).toBeInTheDocument();
    });
  });

  describe('Responsive Behavior', () => {
    it('should maintain container query setup for responsive design', () => {
      // Arrange & Act
      const { container } = render(
        <ResponsivePanel title="Responsive Test">
          <div>Content that adapts</div>
        </ResponsivePanel>
      );

      // Assert
      const panel = container.querySelector('.responsive-panel');
      expect(panel).toHaveStyle({
        containerType: 'inline-size',
        containerName: 'panel',
      });
    });

    it('should handle dynamic content changes', () => {
      // Arrange
      const { rerender } = render(
        <ResponsivePanel title="Dynamic Panel">
          <div>Initial Content</div>
        </ResponsivePanel>
      );

      // Act
      rerender(
        <ResponsivePanel title="Dynamic Panel">
          <div>Updated Content</div>
        </ResponsivePanel>
      );

      // Assert
      expect(screen.getByText('Updated Content')).toBeInTheDocument();
      expect(screen.queryByText('Initial Content')).not.toBeInTheDocument();
    });

    it('should handle title changes', () => {
      // Arrange
      const { rerender } = render(
        <ResponsivePanel title="Original Title">
          <div>Content</div>
        </ResponsivePanel>
      );

      // Act
      rerender(
        <ResponsivePanel title="Updated Title">
          <div>Content</div>
        </ResponsivePanel>
      );

      // Assert
      expect(screen.getByText('Updated Title')).toBeInTheDocument();
      expect(screen.queryByText('Original Title')).not.toBeInTheDocument();
    });

    it('should handle title removal', () => {
      // Arrange
      const { rerender, container } = render(
        <ResponsivePanel title="Title">
          <div>Content</div>
        </ResponsivePanel>
      );

      // Act
      rerender(
        <ResponsivePanel>
          <div>Content</div>
        </ResponsivePanel>
      );

      // Assert
      expect(container.querySelector('header')).not.toBeInTheDocument();
      expect(screen.queryByText('Title')).not.toBeInTheDocument();
    });
  });
});
