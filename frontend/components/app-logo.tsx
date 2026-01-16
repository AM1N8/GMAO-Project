import Link from 'next/link';
import { Wrench } from 'lucide-react';

import { cn } from '@kit/ui/utils';

function LogoImage({
  className,
}: {
  className?: string;
  width?: number;
}) {
  return (
    <div className={cn("flex items-center transition-all hover:opacity-80 active:scale-95", className)}>
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-blue-800 shadow-sm ring-1 ring-white/20">
        <Wrench className="h-5 w-5 text-white" />
      </div>
    </div>
  );
}

export function AppLogo({
  href,
  label,
  className,
}: {
  href?: string | null;
  className?: string;
  label?: string;
}) {
  if (href === null) {
    return <LogoImage className={className} />;
  }

  return (
    <Link aria-label={label ?? 'Home Page'} href={href ?? '/'}>
      <LogoImage className={className} />
    </Link>
  );
}
