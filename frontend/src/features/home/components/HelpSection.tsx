import Reveal from '../../../components/common/Reveal';
import { GLASS } from '../../../utils/styles';

const TIPS = [
  'Enter your School ID exactly as it appears on your records.',
  'Use the eye icon in the password field to check what you typed.',
  'If you do not have an account yet, use Get Started.',
  'For other concerns, see the Contact section.',
];

export default function HelpSection() {
  return (
    <section id="help" className="screen-section scroll-mt-16 py-14 md:py-16">
      <div className="mx-auto w-full max-w-[1920px] px-4 sm:px-6 lg:px-8">
        <Reveal>
          <h2 className="fg-strong text-2xl font-bold">Help</h2>
          <p className="fg-body mt-2 text-sm">Having trouble accessing the portal? Start here.</p>
        </Reveal>
        <Reveal delay={100} className={`mt-5 rounded-2xl p-6 ${GLASS}`}>
          <ul className="grid gap-x-8 gap-y-3 sm:grid-cols-2">
            {TIPS.map((t) => (
              <li key={t} className="fg-body flex gap-3 text-sm">
                <span className="dot-accent mt-2 h-1.5 w-1.5 shrink-0 rounded-full" />
                {t}
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </section>
  );
}
