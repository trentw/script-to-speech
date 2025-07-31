import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { getProviderMeta } from '@/constants/providerMeta';
import { cn } from '@/lib/utils';

interface ProviderAvatarProps {
  provider: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

const sizeClasses = {
  sm: 'h-8 w-8',
  md: 'h-10 w-10',
  lg: 'h-12 w-12',
};

const iconSizeClasses = {
  sm: 'h-4 w-4',
  md: 'h-5 w-5',
  lg: 'h-6 w-6',
};

export function ProviderAvatar({
  provider,
  className,
  size = 'md',
}: ProviderAvatarProps) {
  const config = getProviderMeta(provider);
  const Icon = config.icon;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Avatar className={cn(sizeClasses[size], className)}>
          <AvatarFallback
            className={cn(
              'flex items-center justify-center',
              config.bgColor,
              config.iconColor
            )}
          >
            <Icon className={iconSizeClasses[size]} />
          </AvatarFallback>
        </Avatar>
      </TooltipTrigger>
      <TooltipContent>
        <p>{config.name}</p>
      </TooltipContent>
    </Tooltip>
  );
}
