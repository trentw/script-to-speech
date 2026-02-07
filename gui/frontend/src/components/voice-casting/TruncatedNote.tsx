import { useEffect, useRef, useState } from 'react';

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

const lineClampClass = {
  1: 'line-clamp-1',
  2: 'line-clamp-2',
  3: 'line-clamp-3',
} as const;

interface TruncatedNoteProps {
  text: string;
  label?: string;
  maxLines?: 1 | 2 | 3;
  className?: string;
  labelClassName?: string;
}

export function TruncatedNote({
  text,
  label,
  maxLines = 1,
  className,
  labelClassName,
}: TruncatedNoteProps) {
  const textRef = useRef<HTMLSpanElement>(null);
  const [isTruncated, setIsTruncated] = useState(false);

  useEffect(() => {
    const el = textRef.current;
    if (el) {
      setIsTruncated(el.scrollHeight > el.clientHeight);
    }
  }, [text]);

  const content = (
    <p className={cn('text-xs', className)}>
      {label && (
        <span className={cn('text-muted-foreground', labelClassName)}>
          {label}{' '}
        </span>
      )}
      <span
        ref={textRef}
        className={cn('inline-block w-full', lineClampClass[maxLines])}
      >
        {text}
      </span>
    </p>
  );

  if (!isTruncated) {
    return content;
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>{content}</TooltipTrigger>
      <TooltipContent className="max-w-sm">
        <p className="text-sm whitespace-pre-wrap">
          {label && <span className="font-medium">{label} </span>}
          {text}
        </p>
      </TooltipContent>
    </Tooltip>
  );
}
