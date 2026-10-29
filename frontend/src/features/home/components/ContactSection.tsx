import Reveal from '../../../components/common/Reveal';
import { GLASS } from '../../../utils/styles';

const DETAILS = [
  { label: 'Office', value: '[Official office name – to be added]' },
  { label: 'Email', value: '[Official email address – to be added]' },
  { label: 'Phone', value: '[Official phone number – to be added]' },
  { label: 'Address', value: '[Official campus address – to be added]' },
];

export default function ContactSection() {
  return (
    <section id="contact" className="screen-section scroll-mt-16 py-14 md:py-16">
      <div className="mx-auto w-full max-w-[1920px] px-4 sm:px-6 lg:px-8">
        <Reveal>
          <h2 className="fg-strong text-2xl font-bold">Contact</h2>
        </Reveal>
        <dl className="mt-6 grid gap-4 sm:grid-cols-2">
          {DETAILS.map((d, i) => (
            <Reveal key={d.label} delay={i * 90} className={`rounded-2xl p-5 ${GLASS}`}>
              <dt className="fg-muted text-xs font-medium uppercase tracking-wide">{d.label}</dt>
              <dd className="fg-body mt-1 text-sm">{d.value}</dd>
            </Reveal>
          ))}
        </dl>
      </div>
    </section>
  );
}
