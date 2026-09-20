import { Navbar } from '@/components/landing/Navbar';
import { HeroSection } from '@/components/landing/HeroSection';
import { FeaturesSection } from '@/components/landing/FeaturesSection';
import { HowItWorksSection } from '@/components/landing/HowItWorksSection';
import { ComparisonSection } from '@/components/landing/ComparisonSection';
import { SecuritySection } from '@/components/landing/SecuritySection';
import { Footer } from '@/components/landing/Footer';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Fixed navbar */}
      <Navbar />

      <main>
        {/* 1. Hero — "See Patterns. Understand Crime." */}
        <HeroSection />

        {/* 2. Capabilities — Crime Trends, Hotspot, Prediction, Investigation */}
        <FeaturesSection />

        {/* 3. How It Works — Analyze → Learn → Generate */}
        <HowItWorksSection />

        {/* 4. Deep Learning — GRU, CNN, FT-Transformer, N-BEATS */}
        <ComparisonSection />

        {/* 5. Responsible AI — "Decision Support, Not Decision Making." */}
        <SecuritySection />
      </main>

      {/* Final CTA + minimal footer */}
      <Footer />
    </div>
  );
}
