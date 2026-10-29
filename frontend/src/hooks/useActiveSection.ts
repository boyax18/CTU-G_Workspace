import { useEffect, useState } from 'react';

export function useActiveSection(ids: readonly string[]) {
  const [active, setActive] = useState<string>(ids[0] ?? '');

  useEffect(() => {
    const updateActive = () => {
      if (
        window.scrollY + window.innerHeight >=
        document.documentElement.scrollHeight - 2
      ) {
        setActive(ids[ids.length - 1] ?? '');
        return;
      }

      const marker = window.innerHeight * 0.3;
      let current = ids[0] ?? '';

      for (const id of ids) {
        const section = document.getElementById(id);

        if (section && section.getBoundingClientRect().top <= marker) {
          current = id;
        }
      }

      setActive(current);
    };

    updateActive();
    window.addEventListener('scroll', updateActive, { passive: true });
    window.addEventListener('resize', updateActive);

    return () => {
      window.removeEventListener('scroll', updateActive);
      window.removeEventListener('resize', updateActive);
    };
  }, [ids]);

  return {
    active,
    activate: setActive,
  };
}
