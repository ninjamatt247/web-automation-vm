import AboutHero from '@/components/sections/about-hero';
import AboutLogos from '@/components/sections/about-logos';
import AboutNews from '@/components/sections/about-news';
import AboutTeam from '@/components/sections/about-team';
import Features from '@/components/sections/features';

export default function AboutPage() {
  return (
    <>
      <AboutHero />
      <AboutLogos />
      <AboutTeam />
      <AboutNews />
      <Features className="section-padding" />
    </>
  );
}
