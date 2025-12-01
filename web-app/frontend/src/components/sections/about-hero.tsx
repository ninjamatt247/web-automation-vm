import Image from 'next/image';

export default function AboutHero() {
  return (
    <section className="section-padding container">
      <div className="flex w-fit items-center rounded-full border p-1 text-xs">
        <span className="bg-muted rounded-full px-3 py-1">What’s New?</span>
        <span className="px-3">Introducing Plasma 2.0</span>
      </div>

      <h1 className="my-5 text-5xl leading-none tracking-tight lg:text-7xl">
        Built for control. Backed by community.
        <br className="hidden sm:block" />
        Powered by code.
      </h1>

      <p className="text-muted-foreground leading-snug md:text-lg lg:text-xl">
        Plasma is an open-source, local-first automation platform for people who
        value speed, precision, and autonomy. We believe automation should live
        where your work does — on your machine. That means no third-party
        servers, no forced integrations, and no silent failures. Whether
        you&apos;re scripting simple file routines or building multi-step,
        logic-heavy flows, Plasma puts you in the driver’s seat. Visual when it
        helps. Text-based when it matters.
        <br />
        <br />
        We believe good software should be scriptable, inspectable, and fully
        yours. That’s why Plasma is open source, privacy-respecting, and built
        to adapt to your needs—not the other way around.
      </p>

      <Image
        src="/images/about/hero.webp"
        alt="Plasma"
        width={1920}
        height={1280}
        priority
        className="mt-16 aspect-video object-cover object-top"
      />
    </section>
  );
}
