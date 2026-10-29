import Reveal from '../../../components/common/Reveal';
import { GLASS } from '../../../utils/styles';

export default function AboutSection() {
  return (
    <section id="about" className="screen-section scroll-mt-16 py-14 md:py-16">
      <div className="mx-auto w-full max-w-[1920px] px-4 sm:px-6 lg:px-8">
        <Reveal>
          <h2 className="fg-strong text-2xl font-bold">About</h2>
        </Reveal>
        <Reveal delay={100} className={`mt-4 rounded-2xl p-6 ${GLASS}`}>
          <p className="fg-body max-w-3xl text-sm leading-relaxed">
            CTU-G Workspace is a centralized campus system for Cebu Technological University – Ginatilan Campus. It
            brings campus services and information into one place, and organizes access so that each user sees what
            their authorized account allows.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
