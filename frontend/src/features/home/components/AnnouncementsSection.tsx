import Reveal from '../../../components/common/Reveal';
import { GLASS } from '../../../utils/styles';

export default function AnnouncementsSection() {
  return (
    <section id="announcements" className="screen-section scroll-mt-16 py-14 md:py-16">
      <div className="mx-auto w-full max-w-[1920px] px-4 sm:px-6 lg:px-8">
        <Reveal>
          <h2 className="fg-strong text-2xl font-bold">Announcements</h2>
          <p className="fg-body mt-2 text-sm">General campus announcements appear here.</p>
        </Reveal>
        <Reveal delay={100} className={`mt-5 rounded-2xl p-6 ${GLASS}`}>
          <p className="fg-muted text-sm">No announcements have been posted yet.</p>
        </Reveal>
      </div>
    </section>
  );
}