'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { SignInButton, SignedIn, SignedOut, UserButton } from '@clerk/nextjs';

const navLinks = [
  { href: '/', label: 'Matches' },
  { href: '/stats', label: 'Player Stats', protected: true },
  { href: '/settings', label: 'Settings', protected: true },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="bg-[#111827] border-b border-[#1C2333] px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-8">
        <Link href="/" className="text-xl font-bold tracking-tight">
          <span className="text-[#FF4B44]">GOALS</span>
        </Link>
        <div className="flex gap-6">
          {navLinks.map(({ href, label, protected: isProtected }) => (
            <SignedIn key={href}>
              <Link
                href={href}
                className={`text-sm transition-colors ${
                  pathname === href
                    ? 'text-[#FF4B44] font-medium'
                    : 'text-[#8B95A8] hover:text-[#F0F2F8]'
                }`}
              >
                {label}
              </Link>
            </SignedIn>
          ))}
          <SignedOut>
            <Link
              href="/"
              className={`text-sm ${pathname === '/' ? 'text-[#FF4B44] font-medium' : 'text-[#8B95A8] hover:text-[#F0F2F8]'}`}
            >
              Matches
            </Link>
          </SignedOut>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <SignedOut>
          <SignInButton mode="modal">
            <button className="bg-[#FF4B44] hover:bg-[#FF7A00] text-white text-sm px-4 py-2 rounded-lg transition-colors">
              Sign In
            </button>
          </SignInButton>
        </SignedOut>
        <SignedIn>
          <UserButton afterSignOutUrl="/" />
        </SignedIn>
      </div>
    </nav>
  );
}
