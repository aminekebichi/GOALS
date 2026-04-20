'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { SignInButton, SignOutButton, UserButton, useAuth } from '@clerk/nextjs';

const publicLinks = [{ href: '/', label: 'Matches' }];
const protectedLinks = [
  { href: '/stats', label: 'Player Stats' },
  { href: '/settings', label: 'Settings' },
];

export default function Navbar() {
  const pathname = usePathname();
  const { isSignedIn } = useAuth();

  const allLinks = isSignedIn ? [...publicLinks, ...protectedLinks] : publicLinks;

  return (
    <nav className="bg-[#111827] border-b border-[#1C2333] px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-8">
        <Link href="/" className="text-xl font-bold tracking-tight">
          <span className="text-[#FF4B44]">GOALS</span>
        </Link>
        <div className="flex gap-6">
          {allLinks.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`text-sm transition-colors ${
                pathname === href
                  ? 'text-[#FF4B44] font-medium'
                  : 'text-[#8B95A8] hover:text-[#F0F2F8]'
              }`}
            >
              {label}
            </Link>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-4">
        {isSignedIn ? (
          <UserButton />
        ) : (
          <SignInButton mode="modal">
            <button className="bg-[#FF4B44] hover:bg-[#FF7A00] text-white text-sm px-4 py-2 rounded-lg transition-colors">
              Sign In
            </button>
          </SignInButton>
        )}
      </div>
    </nav>
  );
}
