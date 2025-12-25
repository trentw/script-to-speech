'use client';

import * as SwitchPrimitives from '@radix-ui/react-switch';
import { type VariantProps } from 'class-variance-authority';
import * as React from 'react';

import { cn } from '@/lib/utils';

import { switchThumbVariants, switchVariants } from './switch.variants';

const Switch = React.forwardRef<
  React.ElementRef<typeof SwitchPrimitives.Root>,
  React.ComponentPropsWithoutRef<typeof SwitchPrimitives.Root> &
    VariantProps<typeof switchVariants>
>(({ className, size, ...props }, ref) => (
  <SwitchPrimitives.Root
    className={cn(switchVariants({ size, className }))}
    {...props}
    ref={ref}
  >
    <SwitchPrimitives.Thumb className={cn(switchThumbVariants({ size }))} />
  </SwitchPrimitives.Root>
));
Switch.displayName = SwitchPrimitives.Root.displayName;

export { Switch };
