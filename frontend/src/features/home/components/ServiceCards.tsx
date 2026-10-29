import type { ComponentType, SVGProps } from 'react';
import Reveal from '../../../components/common/Reveal';
import { ClipboardCheckIcon, MonitorIcon, UsersIcon, WalletIcon } from '../../../components/common/Icons';
import { GLASS } from '../../../utils/styles';

interface Service {
  title: string;
  description: string;
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
}

const SERVICES: Service[] = [
  { title: 'SSG Finance', description: 'Organizational fees and payment records, available to authorized accounts.', Icon: WalletIcon },
  { title: 'Clearance', description: 'Track clearance requirements and status through your account.', Icon: ClipboardCheckIcon },
  { title: 'Class Monitoring', description: 'Class and attendance information for authorized users.', Icon: UsersIcon },
  { title: 'COM Lab Inventory', description: 'Computer laboratory equipment records for authorized staff.', Icon: MonitorIcon },
];

export default function ServiceCards() {
  return (
    <section id="services" className="screen-section scroll-mt-16 py-14 md:py-16">
      <div className="mx-auto w-full max-w-[1920px] px-4 sm:px-6 lg:px-8">
        <Reveal>
          <h2 className="fg-strong text-2xl font-bold">Services</h2>
          <p className="fg-body mt-2 max-w-2xl text-sm">
            An overview of the services in CTU-G Workspace. Sign in to use the modules available to your account.
          </p>
        </Reveal>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {SERVICES.map(({ title, description, Icon }, i) => (
            <Reveal key={title} delay={i * 90} className={`lift rounded-2xl p-5 ${GLASS}`}>
              <span className="chip-accent flex h-10 w-10 items-center justify-center rounded-lg">
                <Icon />
              </span>
              <h3 className="fg-strong mt-4 text-base font-semibold">{title}</h3>
              <p className="fg-body mt-1.5 text-sm leading-relaxed">{description}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
