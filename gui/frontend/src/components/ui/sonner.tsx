import { useTheme } from 'next-themes';
import { Toaster as Sonner, type ToasterProps } from 'sonner';

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = 'system' } = useTheme();

  return (
    <Sonner
      theme={theme as ToasterProps['theme']}
      className="toaster group"
      style={
        {
          '--normal-bg': '#ffffff',
          '--success-bg': '#ffffff',
          '--info-bg': '#ffffff',
          '--warning-bg': '#ffffff',
          '--error-bg': '#ffffff',
          '--normal-text': 'var(--foreground)',
          '--success-text': 'var(--foreground)',
          '--info-text': 'var(--foreground)',
          '--warning-text': 'var(--foreground)',
          '--error-text': 'var(--foreground)',
          '--normal-border': 'var(--border)',
          '--success-border': 'var(--border)',
          '--info-border': 'var(--border)',
          '--warning-border': 'var(--border)',
          '--error-border': 'var(--border)',
        } as React.CSSProperties
      }
      {...props}
    />
  );
};

export { Toaster };
