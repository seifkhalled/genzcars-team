import Image from 'next/image'
import Link from 'next/link'
import { getSiteAssetUrl } from '@/lib/site-assets'

export function Footer() {
  return (
    <footer className="bg-surface border-t border-surface-border mt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <Image src={getSiteAssetUrl('logo.png')} alt="Deals" width={80} height={80} className="rounded-lg" />
              <span className="text-lg font-bold text-text-primary">Deals</span>
            </div>
            <p className="text-sm text-text-secondary max-w-md">
              Egypt&apos;s AI-powered car marketplace. Find your perfect car with smart search,
              compare listings side by side, and get expert advice from our AI assistant.
            </p>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-text-primary mb-3">Quick Links</h3>
            <div className="flex flex-col gap-2">
              <Link href="/" className="text-sm text-text-secondary hover:text-primary-500 transition-colors">Browse Cars</Link>
              <Link href="/ads/new" className="text-sm text-text-secondary hover:text-primary-500 transition-colors">Sell Your Car</Link>
              <Link href="/search" className="text-sm text-text-secondary hover:text-primary-500 transition-colors">Search</Link>
              <Link href="/compare" className="text-sm text-text-secondary hover:text-primary-500 transition-colors">Compare</Link>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-text-primary mb-3">Support</h3>
            <div className="flex flex-col gap-2">
              <Link href="/chat" className="text-sm text-text-secondary hover:text-primary-500 transition-colors">AI Assistant</Link>
              <span className="text-sm text-text-secondary">Contact: support@dealsegypt.com</span>
            </div>
          </div>
        </div>

        <div className="mt-8 pt-8 border-t border-surface-border">
          <p className="text-sm text-text-muted text-center">
            &copy; {new Date().getFullYear()} Deals Egypt. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  )
}
