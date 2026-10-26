const STEPS = [
  { title: 'Sign in', description: 'Use your School ID and password to access your account.' },
  { title: 'Open your services', description: 'See the modules your authorized account allows.' },
  { title: 'Stay informed', description: 'Read general campus information on the public pages.' },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-16 bg-[#eef6ef] py-14 md:py-16">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <h2 className="text-2xl font-bold text-gray-900">How It Works</h2>
        <ol className="mt-8 grid gap-4 md:grid-cols-3">
          {STEPS.map((s, i) => (
            <li key={s.title} className="rounded-2xl border border-gray-200 bg-white p-5">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-green-800 text-sm font-semibold text-white">
                {i + 1}
              </span>
              <h3 className="mt-4 text-base font-semibold text-gray-900">{s.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-gray-600">{s.description}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}