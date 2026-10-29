import Button from '../../../components/common/Button';
import Reveal from '../../../components/common/Reveal';
import { LockIcon } from '../../../components/common/Icons';
import { CAMPUS_NAME, REGISTER_PATH } from '../../../utils/constants';
import { scrollToSection } from '../../../utils/scroll';
import HomeLoginForm from './HomeLoginForm';

export default function HeroSection() {
  return (
    <section id="home" className="screen-section scroll-mt-16 relative">
      <div className="mx-auto grid w-full max-w-[1920px] items-center gap-10 px-4 pb-16 pt-12 sm:px-6 md:pb-20 md:pt-16 lg:grid-cols-2 lg:gap-16 lg:px-8 lg:pb-24 lg:pt-20">
        <div className="flex flex-col items-center text-center">
          <Reveal className="pill w-fit rounded-full px-3.5 py-1.5 text-xs font-medium sm:text-sm">
            {CAMPUS_NAME}
          </Reveal>

          <Reveal delay={90}>
            <h1 className="fg-strong mt-6 text-3xl font-bold leading-tight sm:text-4xl lg:text-5xl">
              One Campus.
              <br />
              Connected Services.
            </h1>
          </Reveal>

          <Reveal delay={180}>
            <p className="fg-body mt-5 max-w-lg text-sm leading-relaxed">
              Access campus services through one centralized system: organizational fees, clearance, academic
              information, and announcements, with access based on your authorized account.
            </p>
          </Reveal>

          <Reveal delay={270} className="mt-7 flex w-full flex-col justify-center gap-3 sm:w-auto sm:flex-row">
            {REGISTER_PATH && (
              <Button onClick={() => window.location.assign(REGISTER_PATH as string)}>Get Started</Button>
            )}
            <Button variant="secondary" onClick={() => scrollToSection('services')}>Explore Services</Button>
          </Reveal>

          <Reveal delay={360}>
            <p className="fg-muted mt-8 flex items-start justify-center gap-2 text-xs">
              <LockIcon width={14} height={14} className="mt-0.5 shrink-0" />
              Sign-in is required for personal records. Public pages show general information only.
            </p>
          </Reveal>
        </div>

        <div className="flex justify-center">
          <HomeLoginForm />
        </div>
      </div>
    </section>
  );
}
