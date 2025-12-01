import Image from 'next/image';

import {
  Carousel,
  CarouselContent,
  CarouselItem,
} from '@/components/ui/carousel';

const teamMembers = [
  {
    name: 'Alex Johnson',
    role: 'Lead Engineer',
    image: '/images/about/team/1.webp',
  },
  {
    name: 'Sarah Chen',
    role: 'Product Designer',
    image: '/images/about/team/2.webp',
  },
  {
    name: 'Marcus Rodriguez',
    role: 'Backend Developer',
    image: '/images/about/team/3.webp',
  },
  {
    name: 'Emily Thompson',
    role: 'Frontend Developer',
    image: '/images/about/team/4.webp',
  },
];

export default function AboutTeam() {
  return (
    <section className="section-padding container max-w-screen-xl">
      <h2 className="text-4xxl leading-tight tracking-tight md:text-5xl">
        Meet the Plasma team!
      </h2>
      <p className="text-muted-foreground mt-3 max-w-2xl text-lg leading-snug">
        Plasma is built by a small team of designers, engineers, and open
        source contributors passionate about developer tooling and local-first
        software.
      </p>

      <Carousel
        className="mt-10"
        opts={{
          align: 'start',
          loop: false,
        }}
      >
        <CarouselContent className="cursor-grab snap-x snap-mandatory">
          {teamMembers.map((member, index) => (
            <CarouselItem
              key={index}
              className="min-w-[289px] basis-1/4 snap-start"
            >
              <Image
                src={member.image}
                alt={member.name}
                width={289}
                height={358}
              />
              <h3 className="text-accent-foreground mt-4 text-2xl font-bold">
                {member.name}
              </h3>
              <p className="text-muted-foreground">{member.role}</p>
            </CarouselItem>
          ))}
        </CarouselContent>
      </Carousel>
    </section>
  );
}
