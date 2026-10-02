"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import "./landing.css";
import { LandingBody } from "./body.generated";
import { INTENTS, RAW_STEPS, STATES } from "./data.generated";

const OPTIONS: [string, string][] = [
  ["older_leaves", "Older leaves"],
  ["younger_leaves", "Younger leaves"],
  ["both", "Both"],
];

/**
 * The landing page. The markup, CSS and copy are the Claude Design export, converted mechanically
 * (scripts/convert-landing.py); this file is the export's small script ported to React, with the same timings:
 * the nav turns solid after 60px, the hero art moves at a quarter of the scroll speed, sections reveal once as they
 * enter, and the "one real run" trace replays when it first scrolls into view.
 */
export function Landing() {
  const [step, setStep] = useState(6);
  const [scrolled, setScrolled] = useState(false);
  const [anim, setAnim] = useState(false);
  const [sy, setSy] = useState(0);
  const [pick, setPick] = useState<string | null>(null);
  const [needle, setNeedle] = useState(64.8);
  const timer = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  const play = useCallback(() => {
    clearInterval(timer.current);
    setStep(0);
    setPick(null);
    setNeedle(0);
    let n = 0;
    timer.current = setInterval(() => {
      n += 1;
      if (n >= 6) {
        clearInterval(timer.current);
        setStep(6);
        setTimeout(() => setNeedle(64.8), 80);
      } else setStep(n);
    }, 650);
  }, []);

  useEffect(() => {
    const onScroll = () => {
      const y = window.scrollY || 0;
      setScrolled(y > 60);
      const next = Math.min(y, 900) * 0.25;
      setSy((prev) => (Math.abs(next - prev) > 2 ? next : prev));
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    if (typeof IntersectionObserver === "undefined") return () => window.removeEventListener("scroll", onScroll);

    // Reveal animations are switched on only once the browser can observe scrolling (as in the original), so a visitor
    // without JavaScript, or without IntersectionObserver, sees all of the content.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAnim(true);
    let io: IntersectionObserver | undefined;
    let io2: IntersectionObserver | undefined;
    const t0 = setTimeout(() => {
      io = new IntersectionObserver(
        (entries) => {
          entries.forEach((e) => {
            if (e.isIntersecting) {
              e.target.classList.add("is-in");
              io?.unobserve(e.target);
            }
          });
        },
        { threshold: 0.12, rootMargin: "0px 0px -6% 0px" },
      );
      document.querySelectorAll(".km [data-r]").forEach((el) => io?.observe(el));
      const trace = document.getElementById("km-trace");
      if (trace) {
        io2 = new IntersectionObserver(
          (entries) => {
            if (entries[0]?.isIntersecting) {
              play();
              io2?.disconnect();
            }
          },
          { threshold: 0.35 },
        );
        io2.observe(trace);
      }
    }, 60);
    return () => {
      window.removeEventListener("scroll", onScroll);
      io?.disconnect();
      io2?.disconnect();
      clearTimeout(t0);
      clearInterval(timer.current);
    };
  }, [play]);

  const scrollTrack = (dir: number) => {
    const track = document.getElementById("km-track");
    if (!track) return;
    const card = track.querySelector(".km-slide");
    const w = card ? card.getBoundingClientRect().width + 28 : 440;
    track.scrollBy({ left: dir * w, behavior: "smooth" });
  };

  const steps = RAW_STEPS.map((r, i) => ({
    ...r,
    cls: i < step ? (r.skip ? "is-skipped" : "is-done") : i === step ? "is-active" : "",
  }));
  const leafOpts = OPTIONS.map(([code, label]) => {
    const on = pick === code;
    return {
      label,
      bg: on ? "#E2CF9F" : "transparent",
      fg: on ? "#233A2A" : "#F2EEE5",
      border: on ? "#E2CF9F" : "rgba(242,238,229,.4)",
      pick: () => setPick(code),
    };
  });

  return (
    <LandingBody
      rootClass={anim ? "km-anim" : ""}
      navClass={scrolled ? "is-solid" : ""}
      parallax={sy}
      needle={needle}
      showResult={step >= 6}
      prev={() => scrollTrack(-1)}
      next={() => scrollTrack(1)}
      play={() => play()}
      intents={INTENTS}
      steps={steps}
      leafOpts={leafOpts}
      states={STATES}
    />
  );
}
