import Reveal from '../../../components/common/Reveal';
import { GLASS } from '../../../utils/styles';

const STEPS = [
  { title: 'Sign in', description: 'Use your School ID and password to access your account.' },
  { title: 'Open your services', description: 'See the modules your authorized account allows.' },
  { title: 'Stay informed', description: 'Read general campus information on the public pages.' },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="screen-section scroll-mt-16 py-14 md:py-16">
      <div className="mx-auto w-full max-w-[1920px] px-4 sm:px-6 lg:px-8">
        <Reveal>
          <h2 className="fg-strong text-2xl font-bold">How It Works</h2>
        </Reveal>
        <ol className="mt-8 grid gap-4 md:grid-cols-3">
          {STEPS.map((s, i) => (
            <Reveal key={s.title} as="li" delay={i * 90} className={`rounded-2xl p-5 ${GLASS}`}>
              <span className="chip-accent flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold">
                {i + 1}
              </span>
              <h3 className="fg-strong mt-4 text-base font-semibold">{s.title}</h3>
              <p className="fg-body mt-1.5 text-sm leading-relaxed">{s.description}</p>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}