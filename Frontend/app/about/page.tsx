import { Car, Bot, BarChart3, Shield, MapPin } from 'lucide-react'
import type { Metadata } from 'next'
import { AboutStats } from '@/components/home/AboutStats'

export const metadata: Metadata = {
  title: 'About Us — Deals Egypt',
  description: "Learn about Deals Egypt — the AI-powered car marketplace transforming how Egyptians buy and sell cars.",
}

const team = [
  { name: 'Seif Khalled', role: 'CEO & Co-Founder', initials: 'SK' },
  { name: 'Omar', role: 'CTO & Co-Founder', initials: 'OM' },
  { name: 'Ziad Shalaby', role: 'Head of AI', initials: 'ZS' },
  { name: 'Khaled Karam', role: 'Product Lead', initials: 'KK' },
  { name: 'Hussien', role: 'Lead Developer', initials: 'HU' },
]

export default function AboutPage() {
  return (
    <div>
      {/* Hero */}
      <section className="bg-gradient-to-br from-primary-500 via-primary-600 to-primary-700 text-white">
        <div className="max-w-4xl mx-auto px-4 py-20 text-center">
          <Car className="w-12 h-12 mx-auto mb-4 opacity-80" />
          <h1 className="text-4xl md:text-5xl font-bold mb-4">About Deals</h1>
          <p className="text-lg text-primary-100 max-w-2xl mx-auto">
            Egypt&apos;s first AI-powered car marketplace. We&apos;re on a mission to make buying and selling cars
            smarter, faster, and more transparent.
          </p>
        </div>
      </section>

      {/* Stats — live from database */}
      <AboutStats />

      {/* Mission */}
      <section className="max-w-4xl mx-auto px-4 py-16">
        <h2 className="text-2xl font-bold text-text-primary mb-6">Our Mission</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[
            {
              icon: Bot,
              title: 'AI-Powered Search',
              desc: 'Find the perfect car with natural language. Our AI understands what you need, even if you\'re not sure yourself.',
            },
            {
              icon: BarChart3,
              title: 'Smart Comparisons',
              desc: 'Compare any two cars side-by-side with AI-generated insights on price, reliability, and value.',
            },
            {
              icon: Shield,
              title: 'Price Transparency',
              desc: 'Know if a listing is fairly priced with AI market analysis. No more overpaying or underselling.',
            },
            {
              icon: MapPin,
              title: 'Nationwide Coverage',
              desc: 'Listings from across Egypt — Cairo, Alexandria, Giza, and 24+ more cities.',
            },
          ].map((item) => (
            <div key={item.title} className="flex gap-4 p-4 rounded-xl bg-surface border border-surface-border">
              <item.icon className="w-6 h-6 text-primary-500 shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-text-primary">{item.title}</h3>
                <p className="text-sm text-text-muted mt-1">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Team */}
      <section className="bg-surface-secondary border-y border-surface-border">
        <div className="max-w-4xl mx-auto px-4 py-16 text-center">
          <h2 className="text-2xl font-bold text-text-primary mb-2">Meet the Team</h2>
          <p className="text-text-muted mb-10">The people behind Deals</p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
            {team.map((member) => (
              <div key={member.name}>
                <div className="w-16 h-16 rounded-full bg-primary-500/10 flex items-center justify-center mx-auto mb-3">
                  <span className="text-lg font-bold text-primary-500">{member.initials}</span>
                </div>
                <p className="font-semibold text-text-primary text-sm">{member.name}</p>
                <p className="text-xs text-text-muted">{member.role}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-4xl mx-auto px-4 py-16 text-center">
        <h2 className="text-2xl font-bold text-text-primary mb-3">Ready to find your perfect car?</h2>
        <p className="text-text-muted mb-6">Let AI do the heavy lifting.</p>
        <a
          href="/search"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-primary-500 text-white font-semibold hover:bg-primary-600 transition-colors"
        >
          Start Searching
          <Car className="w-4 h-4" />
        </a>
      </section>
    </div>
  )
}
