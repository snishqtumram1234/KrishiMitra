import Link from "next/link";

export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="inline-flex items-center gap-2 font-display text-lg font-bold text-brand">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M5 19C5 10 10 5 20 4c0 10-5 15-14 15" fill="currentColor" />
        <path d="M5 19c3-5 6-8 10-10" stroke="var(--color-surface)" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      KrishiMitra
    </Link>
  );
}
