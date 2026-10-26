import Button from '../../../components/common/Button';
import { LockIcon } from '../../../components/common/Icons';
import { CAMPUS_NAME, REGISTER_PATH } from '../../../utils/constants';
import { scrollToSection } from '../../../utils/scroll';
import HomeLoginForm from './HomeLoginForm';

export default function HeroSection() {
  return (
    <section id="home" className="bg-[#eef6ef]">
      <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 py-12 sm:px-6 md:py-16 lg:grid-cols-2 lg:gap-16 lg:px-8 lg:py-20">
        <div className="flex flex-col items-start">
          <span className="rounded-full border border-green-800/40 bg-white/60 px-3.5 py-1.5 text-xs font-medium text-green-900 sm:text-sm">
            {CAMPUS_NAME}
          </span>

          <h1 className="mt-6 text-3xl font-bold leading-tight text-gray-900 sm:text-4xl lg:text-5xl">
            One Campus.
            <br />
            Connected Services.
          </h1>

          <p className="mt-5 max-w-lg text-sm leading-relaxed text-gray-600">
            Access campus services through one centralized system: organizational fees, clearance, academic
            information, and announcements, with access based on your authorized account.
          </p>

          <div className="mt-7 flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
            {REGISTER_PATH && (
              <Button onClick={() => window.location.assign(REGISTER_PATH as string)}>Get Started</Button>
            )}
            <Button variant="secondary" onClick={() => scrollToSection('services')}>Explore Services</Button>
          </div>

          <p className="mt-8 flex items-start gap-2 text-xs text-gray-500">
            <LockIcon width={14} height={14} className="mt-0.5 shrink-0" />
            Sign-in is required for personal records. Public pages show general information only.
          </p>
        </div>

        <div className="flex justify-center lg:justify-end">
          <HomeLoginForm />
        </div>
      </div>
    </section>
  );
}