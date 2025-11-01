import { Clock, Sparkles } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ComingSoonCardProps {
  title: string;
  description: string;
  features?: string[];
  className?: string;
}

export function ComingSoonCard({
  title,
  description,
  features = [],
  className,
}: ComingSoonCardProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="bg-secondary flex h-10 w-10 items-center justify-center rounded-lg">
            <Sparkles className="text-secondary-foreground h-5 w-5" />
          </div>
          <div className="flex-1">
            <CardTitle className="flex items-center gap-2">
              {title}
              <Badge variant="outline" className="text-xs">
                <Clock className="mr-1 h-3 w-3" />
                Coming Soon
              </Badge>
            </CardTitle>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-muted-foreground">{description}</p>

        {features.length > 0 && (
          <div>
            <h4 className="mb-2 font-medium">Planned Features:</h4>
            <ul className="text-muted-foreground space-y-1 text-sm">
              {features.map((feature, index) => (
                <li key={index} className="flex items-center gap-2">
                  <div className="bg-muted-foreground/50 h-1.5 w-1.5 rounded-full" />
                  {feature}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="bg-muted/50 rounded-lg p-4 text-center">
          <p className="text-muted-foreground text-sm">
            This feature is currently in development and will be available in a
            future release.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
