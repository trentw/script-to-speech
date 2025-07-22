import { describe, expect,it } from 'vitest'

import { render, screen } from '@/test/test-utils'

describe('Test Setup Verification', () => {
  it('should have test utilities configured correctly', () => {
    // Arrange & Act
    const { container } = render(<div data-testid="test">Hello Tests</div>)
    
    // Assert
    expect(screen.getByTestId('test')).toBeInTheDocument()
    expect(screen.getByText('Hello Tests')).toBeInTheDocument()
    expect(container).toBeDefined()
  })

  it('should have jest-dom matchers available', () => {
    // Arrange
    render(<button disabled>Disabled Button</button>)
    
    // Act
    const button = screen.getByRole('button')
    
    // Assert
    expect(button).toBeDisabled()
    expect(button).toHaveTextContent('Disabled Button')
  })
})