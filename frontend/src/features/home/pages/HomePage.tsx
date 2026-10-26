import HeroSection from '../components/HeroSection';
import ServiceCards from '../components/ServiceCards';
import HowItWorks from '../components/HowItWorks';
import AboutSection from '../components/AboutSection';
import AnnouncementsSection from '../components/AnnouncementsSection';
import HelpSection from '../components/HelpSection';
import ContactSection from '../components/ContactSection';

export default function HomePage() {
  return (
    <>
      <HeroSection />
      <ServiceCards />
      <HowItWorks />
      <AboutSection />
      <AnnouncementsSection />
      <HelpSection />
      <ContactSection />
    </>
  );
}