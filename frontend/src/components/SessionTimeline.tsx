import React, { useRef } from 'react';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';

export default function SessionTimeline({ events }: { events: any[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useGSAP(() => {
    // Animate the newest timeline event
    if (events.length > 0) {
      const newEvent = containerRef.current?.lastElementChild;
      if (newEvent && !newEvent.classList.contains('gsap-animated')) {
        gsap.fromTo(newEvent, 
          { x: 50, opacity: 0 }, 
          { x: 0, opacity: 1, duration: 0.5, ease: 'power2.out', onComplete: () => newEvent.classList.add('gsap-animated') }
        );
        
        // Stagger the checks inside it
        const checks = newEvent.querySelectorAll('.timeline-check');
        if (checks.length > 0) {
          gsap.fromTo(checks,
            { y: -10, opacity: 0 },
            { y: 0, opacity: 1, duration: 0.3, stagger: 0.15, ease: 'back.out(2)', delay: 0.3 }
          );
        }
      }
    }
  }, [events]);
  return (
    <div ref={containerRef} className="stitched-line pl-12 py-4">
      {events.length === 0 && <p className="text-ink-faint italic">Awaiting events...</p>}
      {events.map((ev, idx) => (
        <div key={idx} className="relative mb-8 group animate-fade-in-up">
          {/* The Stamp Pill */}
          <div className={`stamp-pill absolute -left-12 mt-1 w-6 h-6 rounded-full flex items-center justify-center border-2 border-paper
            ${ev.type === 'success' ? 'bg-ledger-blue text-paper' : 
              ev.type === 'check' ? 'bg-ledger-amber text-paper' : 
              'bg-ink-faint text-paper'}`}
          >
            {ev.type === 'success' ? '✓' : ev.type === 'check' ? '●' : '○'}
          </div>

          {/* The Content */}
          <div className="flex flex-col md:flex-row gap-2 md:gap-6 rounded px-2 -mx-2 group-hover:bg-highlight transition-colors duration-100">
            <span className="timestamp text-ink-faint pt-1 shrink-0">{ev.time}</span>
            <div className="pt-1 pb-2">
              <p className="text-ink">{ev.desc}</p>
              
              {ev.reason && (
                <p className="code-value text-ink-faint mt-1 text-sm">{ev.reason}</p>
              )}
              
              {ev.checks && (
                <div className="mt-2 space-y-1">
                  {ev.checks.map((chk: string, i: number) => (
                    <span key={i} className="timeline-check code-value text-xs bg-ledger-blue/10 text-ledger-blue px-2 py-0.5 rounded-sm mr-2 inline-block mb-1">
                      {chk}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

