import { FeatureGrid } from "@/components/landing/feature-grid";
import { Hero } from "@/components/landing/hero";
import { StatStrip } from "@/components/landing/stat-strip";

export default function Home() {
  return (
    <main>
      <Hero />
      <StatStrip />
      <FeatureGrid />
    </main>
  );
}
