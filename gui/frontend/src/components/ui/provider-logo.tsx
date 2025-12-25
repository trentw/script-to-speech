import React, { useState } from 'react';

import { getProviderMeta } from '@/constants/providerMeta';
import { cn } from '@/lib/utils';

export interface ProviderLogoProps {
  provider: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeConfig = {
  sm: {
    container: 'h-10 w-10 p-2.5',
    content: 'h-5 w-5',
    text: 'text-sm',
  },
  md: {
    container: 'h-12 w-12 p-3',
    content: 'h-6 w-6',
    text: 'text-base',
  },
  lg: {
    container: 'h-14 w-14 p-3.5',
    content: 'h-7 w-7',
    text: 'text-lg',
  },
};

export const ProviderLogo = React.memo(function ProviderLogo({
  provider,
  size = 'md',
  className,
}: ProviderLogoProps) {
  const [imageError, setImageError] = useState(false);
  const meta = getProviderMeta(provider);
  const config = sizeConfig[size];

  // Container styling - white background with balanced border
  const containerClasses = cn(
    config.container,
    'rounded-full bg-white border border-gray-300',
    'flex items-center justify-center shrink-0',
    className
  );

  // Determine what to render based on availability and load status
  if (meta.logo && !imageError) {
    // Try to render logo image
    return (
      <div className={containerClasses}>
        <img
          src={meta.logo}
          alt={`${meta.name} logo`}
          className={cn(config.content, 'object-contain')}
          onError={() => setImageError(true)}
        />
      </div>
    );
  }

  // Fallback to icon if available
  if (meta.icon) {
    const Icon = meta.icon;
    return (
      <div className={containerClasses}>
        <Icon className={cn(config.content, meta.iconColor)} />
      </div>
    );
  }

  // Final fallback to first letter
  return (
    <div className={containerClasses}>
      <span className={cn(config.text, 'font-semibold', meta.iconColor)}>
        {meta.name.charAt(0).toUpperCase()}
      </span>
    </div>
  );
});

ProviderLogo.displayName = 'ProviderLogo';
