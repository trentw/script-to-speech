import { ProviderLogo } from '@/components/ui/provider-logo';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { getProviderMeta } from '@/constants/providerMeta';

interface ProviderAvatarProps {
  provider: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function ProviderAvatar({
  provider,
  className,
  size = 'md',
}: ProviderAvatarProps) {
  const meta = getProviderMeta(provider);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div>
          <ProviderLogo provider={provider} size={size} className={className} />
        </div>
      </TooltipTrigger>
      <TooltipContent>
        <p>{meta.name}</p>
      </TooltipContent>
    </Tooltip>
  );
}
