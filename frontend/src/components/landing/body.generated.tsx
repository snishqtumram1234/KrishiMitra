// Generated from the Claude Design landing export. Do not edit by hand.
/* eslint-disable */
import { Fragment, type MouseEventHandler } from "react";
import { HeroArt } from "./HeroArt";

export type LandingView = {
  rootClass: string; navClass: string; parallax: number; needle: number; showResult: boolean;
  prev: MouseEventHandler; next: MouseEventHandler; play: MouseEventHandler;
  intents: { num: string; q: string; route: string; what: string; photo: string; state: string }[];
  steps: { step: string; model: string; note: string; ms: string; cls: string }[];
  leafOpts: { label: string; bg: string; fg: string; border: string; pick: MouseEventHandler }[];
  states: { num: string; title: string; code: string; text: string }[];
};

export function LandingBody({ rootClass, navClass, parallax, needle, showResult, prev, next, play, intents, steps, leafOpts, states }: LandingView) {
  return (
<div className={`km ${rootClass}`} style={{ width: "100%", minHeight: "100px" }}>


<div className="km-loader" aria-hidden="true">
<div className="km-serif" style={{ fontSize: "30px", letterSpacing: ".02em", color: "#F2EEE5" }}>KrishiMitra</div>
<div className="km-loader-bar"><span></span></div>
<div className="km-mr" style={{ fontSize: "15px", color: "rgba(242,238,229,.6)" }}>कृषिमित्र</div>
</div>


<header className={`km-nav ${navClass}`}>
<div className="km-wrap" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "24px" }}>
<a href="#top" style={{ display: "flex", alignItems: "center", gap: "12px", color: "#F2EEE5", textDecoration: "none" }} aria-label="KrishiMitra home">
<svg width="30" height="30" viewBox="0 0 32 32" fill="none" stroke="#E2CF9F" strokeWidth="1.4" aria-hidden="true"><path d="M16 29V15"></path><path d="M16 15C16 9 19.5 4.5 25 3c.5 6-3 11-9 12z"></path><path d="M16 15C16 9 12.5 4.5 7 3c-.5 6 3 11 9 12z"></path><path d="M16 21c-4.5 0-8-2.5-9.5-6.5 4.5-.5 8 1.5 9.5 6.5z"></path></svg>
<span className="km-serif" style={{ fontSize: "26px", letterSpacing: ".01em" }}>KrishiMitra</span>
</a>
<nav aria-label="Primary" style={{ display: "flex", alignItems: "center", gap: "40px" }}>
<a className="km-link km-hide-sm" href="#ask">Ask</a>
<a className="km-link km-hide-sm" href="#how">How it works</a>
<a className="km-link km-hide-sm" href="#answers">Answers</a>
<a className="km-link km-hide-sm" href="#experts">Experts</a>
<a className="km-btn" href="/checks/new" style={{ minHeight: "44px", padding: "0 22px" }}><span>Check a leaf</span></a>
</nav>
</div>
</header>


<section id="top" className="km-hero">
<div className="km-hero-art" aria-hidden="true">
<div style={{ width: "100%", height: "100%", transform: `translateY(${parallax}px)` }}>
<HeroArt />
</div>
<div style={{ position: "absolute", inset: "0", background: "linear-gradient(180deg, rgba(35,58,42,.6) 0%, rgba(35,58,42,0) 20%, rgba(35,58,42,0) 40%, rgba(35,58,42,.55) 62%, rgba(35,58,42,.9) 100%)" }}></div>
</div>
<div className="km-wrap" style={{ position: "relative", zIndex: "2", paddingBottom: "72px", paddingTop: "160px" }}>
<h1 className="km-serif" style={{ margin: "0", fontSize: "clamp(68px, 13.5vw, 214px)", lineHeight: ".9", fontWeight: "400", letterSpacing: "-.02em" }}>
<span className="km-line"><span className="km-letter" style={{ animationDelay: "1.45s" }}>K</span><span className="km-letter" style={{ animationDelay: "1.5s" }}>r</span><span className="km-letter" style={{ animationDelay: "1.55s" }}>i</span><span className="km-letter" style={{ animationDelay: "1.6s" }}>s</span><span className="km-letter" style={{ animationDelay: "1.65s" }}>h</span><span className="km-letter" style={{ animationDelay: "1.7s" }}>i</span><span className="km-letter" style={{ animationDelay: "1.75s", fontStyle: "italic", color: "#E2CF9F" }}>M</span><span className="km-letter" style={{ animationDelay: "1.8s", fontStyle: "italic", color: "#E2CF9F" }}>i</span><span className="km-letter" style={{ animationDelay: "1.85s", fontStyle: "italic", color: "#E2CF9F" }}>t</span><span className="km-letter" style={{ animationDelay: "1.9s", fontStyle: "italic", color: "#E2CF9F" }}>r</span><span className="km-letter" style={{ animationDelay: "1.95s", fontStyle: "italic", color: "#E2CF9F" }}>a</span></span>
</h1>
<div className="km-split" style={{ marginTop: "36px" }}>
<p className="km-fade" style={{ gridColumn: "span 6", margin: "0", fontSize: "clamp(18px, 1.6vw, 22px)", lineHeight: "1.55", color: "rgba(242,238,229,.86)", maxWidth: "560px", animationDelay: "2.2s" }}>A careful second opinion for your field. Send a leaf photo or ask a question in English or <span className="km-mr">मराठी</span>, and get a preliminary answer, honest about what it does not know, with a human expert when it matters.</p>
<div className="km-fade" style={{ gridColumn: "8 / span 5", display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: "24px", animationDelay: "2.4s" }}>
<div>
<div style={{ fontSize: "12px", letterSpacing: ".2em", textTransform: "uppercase", color: "rgba(242,238,229,.6)" }}>Answers in</div>
<div className="km-serif" style={{ fontSize: "34px", marginTop: "4px" }}>tens of milliseconds</div>
</div>
<div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" }}>
<span style={{ fontSize: "11px", letterSpacing: ".24em", textTransform: "uppercase", color: "rgba(242,238,229,.7)" }}>(Scroll)</span>
<div className="km-scroll-cue"><span></span></div>
</div>
</div>
</div>
</div>
</section>


<div className="km-marquee" aria-hidden="true">
<div className="km-marquee-track">
<div className="km-serif" style={{ display: "flex", gap: "48px", padding: "26px 24px", fontSize: "30px", whiteSpace: "nowrap", fontStyle: "italic", color: "rgba(242,238,229,.82)" }}>
<span>English &amp; <span className="km-mr" style={{ fontStyle: "normal" }}>मराठी</span></span><span style={{ color: "#E2CF9F" }}>✦</span><span>36 Maharashtra districts</span><span style={{ color: "#E2CF9F" }}>✦</span><span>Never a pesticide dose</span><span style={{ color: "#E2CF9F" }}>✦</span><span>Preliminary, never “confirmed”</span><span style={{ color: "#E2CF9F" }}>✦</span><span>A human expert when it matters</span><span style={{ color: "#E2CF9F" }}>✦</span>
</div>
<div className="km-serif" style={{ display: "flex", gap: "48px", padding: "26px 24px", fontSize: "30px", whiteSpace: "nowrap", fontStyle: "italic", color: "rgba(242,238,229,.82)" }}>
<span>English &amp; <span className="km-mr" style={{ fontStyle: "normal" }}>मराठी</span></span><span style={{ color: "#E2CF9F" }}>✦</span><span>36 Maharashtra districts</span><span style={{ color: "#E2CF9F" }}>✦</span><span>Never a pesticide dose</span><span style={{ color: "#E2CF9F" }}>✦</span><span>Preliminary, never “confirmed”</span><span style={{ color: "#E2CF9F" }}>✦</span><span>A human expert when it matters</span><span style={{ color: "#E2CF9F" }}>✦</span>
</div>
</div>
</div>


<section style={{ background: "#F2EEE5", color: "#1F2E23", padding: "140px 0 150px" }}>
<div className="km-wrap">
<div className="km-split" style={{ alignItems: "center" }}>
<div style={{ gridColumn: "span 6" }}>
<div data-r="" style={{ fontSize: "12px", letterSpacing: ".22em", textTransform: "uppercase", color: "#5A7A3A", marginBottom: "26px" }}>(01) The approach</div>
<h2 data-r="" className="km-serif" style={{ margin: "0", fontSize: "clamp(44px, 5.4vw, 80px)", lineHeight: "1", fontWeight: "400", letterSpacing: "-.01em", transitionDelay: ".1s" }}>The patient way<br />to read a <em style={{ color: "#5A7A3A" }}>leaf</em></h2>
<p data-r="" style={{ margin: "36px 0 0", fontSize: "19px", lineHeight: "1.7", color: "#3F4D42", maxWidth: "520px", transitionDelay: ".2s" }}>KrishiMitra checks every photo for blur, light and leaf before any model looks at it. It says how sure it is: low, medium or high. And when the evidence is thin, it asks one more question or hands your case to an agriculture expert instead of guessing.</p>
<div data-r="" style={{ marginTop: "44px", transitionDelay: ".3s" }}><a className="km-btn is-dark" href="#how"><span>See a real run</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M4 12h16M14 6l6 6-6 6"></path></svg></a></div>
</div>
<div style={{ gridColumn: "8 / span 5" }}>
<figure data-r="clip" className="km-hover-zoom" style={{ margin: "0", position: "relative", aspectRatio: "4 / 5", overflow: "hidden", borderRadius: "2px", background: "#2F4A36" }}>
<div className="km-zoom-inner" style={{ position: "absolute", inset: "0", display: "flex", alignItems: "center", justifyContent: "center" }}>
<svg viewBox="-150 -150 300 300" style={{ width: "82%", height: "82%" }} aria-hidden="true">
<g fill="none" stroke="#E2CF9F" strokeWidth="1.3">
<path d="M0 130 L0 18"></path>
<g transform="translate(0,8)"><path d="M0,-130 C52,-96 56,-22 0,10 C-56,-22 -52,-96 0,-130Z" fill="#E2CF9F" fillOpacity=".08"></path><path d="M0,-124 L0,8"></path><path d="M0,-90 L24,-104 M0,-62 L32,-78 M0,-34 L30,-48 M0,-90 L-24,-104 M0,-62 L-32,-78 M0,-34 L-30,-48"></path></g>
<g transform="translate(0,22) rotate(-62) translate(0,-10)"><path d="M0,-118 C46,-86 50,-20 0,10 C-50,-20 -46,-86 0,-118Z" fill="#E2CF9F" fillOpacity=".05"></path><path d="M0,-112 L0,8"></path><path d="M0,-80 L22,-92 M0,-50 L28,-64 M0,-80 L-22,-92 M0,-50 L-28,-64"></path></g>
<g transform="translate(0,22) rotate(62) translate(0,-10)"><path d="M0,-118 C46,-86 50,-20 0,10 C-50,-20 -46,-86 0,-118Z" fill="#E2CF9F" fillOpacity=".05"></path><path d="M0,-112 L0,8"></path><path d="M0,-80 L22,-92 M0,-50 L28,-64 M0,-80 L-22,-92 M0,-50 L-28,-64"></path></g>
</g>
<g fill="#D98A4E"><circle cx="14" cy="-70" r="4"></circle><circle cx="-18" cy="-52" r="3"></circle><circle cx="22" cy="-40" r="2.5"></circle><circle cx="-8" cy="-92" r="2.5"></circle><circle cx="-60" cy="-38" r="3"></circle></g>
<rect x="-70" y="-120" width="110" height="110" fill="none" stroke="#F2EEE5" strokeWidth="1" strokeDasharray="6 6"></rect>
</svg>
</div>
<figcaption style={{ position: "absolute", left: "24px", right: "24px", bottom: "22px", display: "flex", justifyContent: "space-between", gap: "12px", fontSize: "12px", letterSpacing: ".14em", textTransform: "uppercase", color: "rgba(242,238,229,.8)" }}>
<span>leaf_closeup</span><span className="km-mono" style={{ letterSpacing: "0" }}>rust_like · 0.65 · medium</span>
</figcaption>
</figure>
</div>
</div>
</div>
</section>


<section id="ask" style={{ background: "#2F4A36", padding: "140px 0 150px" }}>
<div className="km-wrap" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: "32px", flexWrap: "wrap", marginBottom: "64px" }}>
<div>
<div data-r="" style={{ fontSize: "12px", letterSpacing: ".22em", textTransform: "uppercase", color: "#E2CF9F", marginBottom: "22px" }}>(02) Ask anything</div>
<h2 data-r="" className="km-serif" style={{ margin: "0", fontSize: "clamp(42px, 5vw, 76px)", lineHeight: "1", fontWeight: "400", maxWidth: "760px", transitionDelay: ".1s" }}>Seven kinds of question, each with its <em>own path</em></h2>
</div>
<div data-r="" style={{ display: "flex", gap: "14px", transitionDelay: ".2s" }}>
<button className="km-arrow" type="button" aria-label="Previous question" onClick={prev}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M20 12H4M10 6l-6 6 6 6"></path></svg></button>
<button className="km-arrow" type="button" aria-label="Next question" onClick={next}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M4 12h16M14 6l6 6-6 6"></path></svg></button>
</div>
</div>
<div data-r="" style={{ transitionDelay: ".25s" }}>
<div id="km-track" className="km-track">
{intents.map((it, __i) => (<Fragment key={__i}>
<article className="km-slide">
<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px" }}>
<span className="km-mono" style={{ fontSize: "13px", color: "rgba(242,238,229,.6)" }}>{it.num} / 07</span>
<span className="km-mono" style={{ fontSize: "12px", padding: "6px 12px", borderRadius: "999px", border: "1px solid rgba(226,207,159,.5)", color: "#E2CF9F" }}>{it.route}</span>
</div>
<div>
<p className="km-serif" style={{ margin: "0", fontSize: "38px", lineHeight: "1.1", fontStyle: "italic" }}>“{it.q}”</p>
<p style={{ margin: "22px 0 0", fontSize: "16px", lineHeight: "1.6", color: "rgba(242,238,229,.76)" }}>{it.what}</p>
</div>
<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", paddingTop: "22px", borderTop: "1px solid rgba(242,238,229,.14)", fontSize: "12px", letterSpacing: ".14em", textTransform: "uppercase" }}>
<span style={{ color: "rgba(242,238,229,.6)" }}>{it.photo}</span>
<span style={{ color: "#F2EEE5" }}>{it.state}</span>
</div>
</article>
</Fragment>))}
<div style={{ flex: "0 0 20px" }}></div>
</div>
</div>
</section>


<section style={{ background: "#F2EEE5", color: "#1F2E23", padding: "150px 0" }}>
<div className="km-wrap" style={{ maxWidth: "1100px", textAlign: "center" }}>
<div data-r="line" style={{ width: "120px", height: "1px", background: "#1F2E23", margin: "0 auto 56px" }}></div>
<blockquote data-r="" className="km-serif" style={{ margin: "0", fontSize: "clamp(34px, 4.2vw, 62px)", lineHeight: "1.15", fontWeight: "400", transitionDelay: ".1s" }}>“Nothing is a confirmed diagnosis. Responses never contain pesticide names or doses. Image-based answers are always labelled <em style={{ color: "#5A7A3A" }}>preliminary</em>.”</blockquote>
<div data-r="" style={{ marginTop: "40px", fontSize: "13px", letterSpacing: ".2em", textTransform: "uppercase", color: "#4F5C51", transitionDelay: ".2s" }}>KrishiMitra / Safety policy / Built into every response</div>
</div>
</section>


<section id="experts" style={{ background: "#F2EEE5", color: "#1F2E23", padding: "0 0 150px" }}>
<div className="km-wrap">
<div className="km-grid3">
<div data-r="">
<div data-r="clip" className="km-hover-zoom" style={{ aspectRatio: "4 / 3", overflow: "hidden", background: "#2F4A36", position: "relative", borderRadius: "2px" }}>
<div className="km-zoom-inner" style={{ position: "absolute", inset: "0", display: "flex", alignItems: "center", justifyContent: "center" }}>
<svg viewBox="0 0 200 150" style={{ width: "70%" }} aria-hidden="true"><g fill="none" stroke="#E2CF9F" strokeWidth="1.2"><rect x="50" y="20" width="100" height="110" rx="4"></rect><path d="M100 112V60"></path><path d="M100 60c0-14 8-24 22-28 2 14-8 26-22 28zM100 74c0-12-7-21-19-24-2 12 7 22 19 24z"></path><path d="M38 34V22h12M162 34V22h-12M38 116v12h12M162 116v12h-12" stroke="#F2EEE5"></path></g></svg>
</div>
</div>
<div className="km-serif" style={{ fontSize: "64px", lineHeight: "1", marginTop: "34px" }}>0–100</div>
<h3 style={{ margin: "12px 0 0", fontSize: "14px", letterSpacing: ".18em", textTransform: "uppercase", fontWeight: "700" }}>Photo check first</h3>
<p style={{ margin: "14px 0 0", fontSize: "17px", lineHeight: "1.65", color: "#3F4D42" }}>A quality score for blur, light, size and leaf presence. A poor photo gets a clear retake tip, like “retake in daylight”, before any model is called.</p>
</div>
<div data-r="" style={{ transitionDelay: ".12s" }}>
<div data-r="clip" className="km-hover-zoom" style={{ aspectRatio: "4 / 3", overflow: "hidden", background: "#2F4A36", position: "relative", borderRadius: "2px", transitionDelay: ".12s" }}>
<div className="km-zoom-inner" style={{ position: "absolute", inset: "0", display: "flex", alignItems: "center", justifyContent: "center" }}>
<svg viewBox="0 0 200 150" style={{ width: "70%" }} aria-hidden="true"><g fill="none" stroke="#E2CF9F" strokeWidth="1.2"><path d="M62 92h78a22 22 0 0 0 0-44 30 30 0 0 0-56-6 24 24 0 0 0-22 50z"></path><path d="M74 106l-6 14M98 106l-6 14M122 106l-6 14" stroke="#F2EEE5"></path></g></svg>
</div>
</div>
<div className="km-serif" style={{ fontSize: "64px", lineHeight: "1", marginTop: "34px" }}>36</div>
<h3 style={{ margin: "12px 0 0", fontSize: "14px", letterSpacing: ".18em", textTransform: "uppercase", fontWeight: "700" }}>Districts, with provenance</h3>
<p style={{ margin: "14px 0 0", fontSize: "17px", lineHeight: "1.65", color: "#3F4D42" }}>Live Open-Meteo forecast data for every Maharashtra district, always labelled: live, cached, demo or unavailable. Old names like Aurangabad still work.</p>
</div>
<div data-r="" style={{ transitionDelay: ".24s" }}>
<div data-r="clip" className="km-hover-zoom" style={{ aspectRatio: "4 / 3", overflow: "hidden", background: "#2F4A36", position: "relative", borderRadius: "2px", transitionDelay: ".24s" }}>
<div className="km-zoom-inner" style={{ position: "absolute", inset: "0", display: "flex", alignItems: "center", justifyContent: "center" }}>
<svg viewBox="0 0 200 150" style={{ width: "70%" }} aria-hidden="true"><g fill="none" stroke="#E2CF9F" strokeWidth="1.2"><circle cx="100" cy="52" r="20"></circle><path d="M62 124c4-24 20-38 38-38s34 14 38 38"></path><path d="M138 40h34v24h-20l-8 8v-8h-6z" stroke="#F2EEE5"></path></g></svg>
</div>
</div>
<div className="km-serif" style={{ fontSize: "64px", lineHeight: "1", marginTop: "34px" }}>1 human</div>
<h3 style={{ margin: "12px 0 0", fontSize: "14px", letterSpacing: ".18em", textTransform: "uppercase", fontWeight: "700" }}>Expert in the loop</h3>
<p style={{ margin: "14px 0 0", fontSize: "17px", lineHeight: "1.65", color: "#3F4D42" }}>Low confidence, a treatment question or a source it can’t verify? Your case goes to an agriculture expert, who can review it or ask you for more.</p>
</div>
</div>
</div>
</section>


<section id="how" style={{ background: "#233A2A", padding: "150px 0" }}>
<div className="km-wrap">
<div className="km-split km-trace-grid" style={{ alignItems: "start", gridTemplateColumns: "repeat(12, minmax(0, 1fr))" }}>
<div style={{ gridColumn: "span 5" }}>
<div data-r="" style={{ fontSize: "12px", letterSpacing: ".22em", textTransform: "uppercase", color: "#E2CF9F", marginBottom: "22px" }}>(03) How it works</div>
<h2 data-r="" className="km-serif" style={{ margin: "0", fontSize: "clamp(42px, 5vw, 74px)", lineHeight: "1", fontWeight: "400", transitionDelay: ".1s" }}>One real run, <em>replayed</em></h2>
<p data-r="" style={{ margin: "30px 0 0", fontSize: "18px", lineHeight: "1.7", color: "rgba(242,238,229,.8)", maxWidth: "460px", transitionDelay: ".2s" }}>“Yellow spots on the leaves”, with a close-up photo from Pune. Every step is recorded with its real timing, including the ones it chose to skip, so nothing about the answer is hidden.</p>
<div data-r="" style={{ marginTop: "40px", display: "flex", gap: "36px", flexWrap: "wrap", transitionDelay: ".3s" }}>
<div><div className="km-serif" style={{ fontSize: "54px", lineHeight: "1" }}>64<span style={{ fontSize: "26px" }}> ms</span></div><div style={{ fontSize: "12px", letterSpacing: ".18em", textTransform: "uppercase", color: "rgba(242,238,229,.6)", marginTop: "6px" }}>Total time</div></div>
<div><div className="km-serif" style={{ fontSize: "54px", lineHeight: "1" }}>$0.00002</div><div style={{ fontSize: "12px", letterSpacing: ".18em", textTransform: "uppercase", color: "rgba(242,238,229,.6)", marginTop: "6px" }}>Estimated cost</div></div>
</div>
<div data-r="" style={{ marginTop: "44px", transitionDelay: ".4s" }}><button className="km-btn" type="button" onClick={play}><span>Replay the run</span><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M4 12a8 8 0 1 0 2.3-5.6M4 4v4h4"></path></svg></button></div>
</div>
<div id="km-trace" style={{ gridColumn: "7 / span 6" }}>
{steps.map((s, __i) => (<Fragment key={__i}>
<div className={`km-step ${s.cls}`}>
<span className="km-dot"></span>
<div>
<div style={{ display: "flex", alignItems: "baseline", gap: "14px", flexWrap: "wrap" }}><span className="km-mono" style={{ fontSize: "16px", color: "#F2EEE5" }}>{s.step}</span><span className="km-mono" style={{ fontSize: "12px", color: "rgba(242,238,229,.55)" }}>{s.model}</span></div>
<div style={{ fontSize: "15px", color: "rgba(242,238,229,.78)", marginTop: "6px" }}>{s.note}</div>
</div>
<span className="km-mono" style={{ fontSize: "14px", color: "#E2CF9F", whiteSpace: "nowrap" }}>{s.ms}</span>
</div>
</Fragment>))}
<div style={{ borderTop: "1px solid rgba(242,238,229,.12)" }}></div>
{showResult && (<>
<div className="km-result" style={{ marginTop: "36px", padding: "32px", background: "#2F4A36", border: "1px solid rgba(242,238,229,.14)", borderRadius: "4px" }}>
<div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
<span style={{ fontSize: "12px", letterSpacing: ".2em", textTransform: "uppercase", color: "#E2CF9F" }}>Preliminary guidance</span>
<span className="km-mono" style={{ fontSize: "12px", color: "rgba(242,238,229,.6)" }}>reason: mid_confidence</span>
</div>
<div style={{ marginTop: "26px" }}>
<div style={{ position: "relative", height: "6px", borderRadius: "3px", background: "rgba(242,238,229,.12)", display: "grid", gridTemplateColumns: "60fr 25fr 15fr", overflow: "visible" }}>
<span style={{ background: "rgba(217,138,78,.55)", borderRadius: "3px 0 0 3px" }}></span><span style={{ background: "rgba(226,207,159,.6)" }}></span><span style={{ background: "rgba(242,238,229,.35)", borderRadius: "0 3px 3px 0" }}></span>
<span className="km-needle" style={{ position: "absolute", top: "-7px", left: `${needle}%`, width: "2px", height: "20px", background: "#F2EEE5" }}></span>
</div>
<div className="km-mono" style={{ display: "grid", gridTemplateColumns: "60fr 25fr 15fr", fontSize: "11px", color: "rgba(242,238,229,.6)", marginTop: "10px" }}><span>low &lt; 0.60</span><span>medium</span><span>high &gt; 0.85</span></div>
</div>
<p style={{ margin: "24px 0 0", fontSize: "17px", lineHeight: "1.65", color: "#F2EEE5" }}>The photo may show signs of rust-like symptoms. This is a preliminary observation, not a confirmed diagnosis. No treatment is suggested at this confidence level.</p>
<p className="km-serif" style={{ margin: "22px 0 14px", fontSize: "24px", fontStyle: "italic" }}>Are the symptoms on older leaves, younger leaves, or both?</p>
<div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
{leafOpts.map((o, __i) => (<Fragment key={__i}>
<button type="button" onClick={o.pick} style={{ minHeight: "44px", padding: "0 20px", borderRadius: "999px", fontFamily: "inherit", fontSize: "14px", cursor: "pointer", border: `1px solid ${o.border}`, background: o.bg, color: o.fg, transition: "all .3s ease" }}>{o.label}</button>
</Fragment>))}
</div>
</div>
</>)}
</div>
</div>
</div>
</section>


<section id="answers" style={{ background: "#F2EEE5", color: "#1F2E23", padding: "150px 0" }}>
<div className="km-wrap">
<div className="km-split" style={{ marginBottom: "70px" }}>
<div style={{ gridColumn: "span 7" }}>
<div data-r="" style={{ fontSize: "12px", letterSpacing: ".22em", textTransform: "uppercase", color: "#5A7A3A", marginBottom: "22px" }}>(04) Five honest answers</div>
<h2 data-r="" className="km-serif" style={{ margin: "0", fontSize: "clamp(42px, 5vw, 76px)", lineHeight: "1", fontWeight: "400", transitionDelay: ".1s" }}>Every case ends in one of five <em style={{ color: "#5A7A3A" }}>clear</em> states</h2>
</div>
<p data-r="" style={{ gridColumn: "9 / span 4", margin: "0", fontSize: "17px", lineHeight: "1.7", color: "#3F4D42", transitionDelay: ".2s" }}>No vague verdicts. Each state tells you exactly what happens next, and what would make the answer better.</p>
</div>
<div className="km-states">
{states.map((st, __i) => (<Fragment key={__i}>
<div className="km-state" data-r="">
<span className="km-mono" style={{ fontSize: "14px", color: "#5A7A3A" }}>{st.num}</span>
<div><h3 className="km-serif" style={{ margin: "0", fontSize: "clamp(28px, 2.8vw, 40px)", fontWeight: "500", lineHeight: "1.1" }}>{st.title}</h3><div className="km-mono" style={{ fontSize: "12px", color: "#4F5C51", marginTop: "8px" }}>{st.code}</div></div>
<p style={{ margin: "0", fontSize: "17px", lineHeight: "1.65", color: "#3F4D42" }}>{st.text}</p>
</div>
</Fragment>))}
<div style={{ borderTop: "1px solid rgba(31,46,35,.16)" }}></div>
</div>
</div>
</section>


<section style={{ position: "relative", background: "#2F4A36", padding: "170px 0", overflow: "hidden" }}>
<div aria-hidden="true" style={{ position: "absolute", inset: "0", opacity: ".5" }}>
<svg viewBox="0 0 1440 700" preserveAspectRatio="xMidYMid slice" style={{ width: "100%", height: "100%" }}><g fill="none" stroke="#E2CF9F" strokeOpacity=".18" strokeWidth="1"><path d="M-20 600 C 300 520 520 640 760 560 S 1200 480 1460 560"></path><path d="M-20 640 C 300 560 520 680 760 600 S 1200 520 1460 600"></path><path d="M-20 680 C 300 600 520 720 760 640 S 1200 560 1460 640"></path><path d="M-20 120 C 300 40 520 160 760 80 S 1200 0 1460 80"></path><path d="M-20 160 C 300 80 520 200 760 120 S 1200 40 1460 120"></path></g></svg>
</div>
<div className="km-wrap" style={{ position: "relative", maxWidth: "1120px", textAlign: "center" }}>
<svg data-r="" width="44" height="34" viewBox="0 0 44 34" fill="#E2CF9F" aria-hidden="true" style={{ margin: "0 auto 40px", display: "block" }}><path d="M0 34V20C0 8 6 1 18 0v6c-6 1-9 5-9 12h9v16zm26 0V20c0-12 6-19 18-20v6c-6 1-9 5-9 12h9v16z"></path></svg>
<blockquote data-r="" className="km-serif" style={{ margin: "0", fontSize: "clamp(30px, 3.6vw, 52px)", lineHeight: "1.2", fontWeight: "400", fontStyle: "italic", transitionDelay: ".1s" }}>KrishiMitra does not give pesticide names or doses. Your question is sent to a human agriculture expert. Meanwhile, contact your local Krishi Vigyan Kendra before spraying anything.</blockquote>
<div data-r="" style={{ marginTop: "40px", fontSize: "13px", letterSpacing: ".2em", textTransform: "uppercase", color: "rgba(242,238,229,.7)", transitionDelay: ".2s" }}>What a treatment question returns / State: Expert review</div>
</div>
</section>


<section id="start" style={{ background: "#F2EEE5", color: "#1F2E23", padding: "160px 0 140px" }}>
<div className="km-wrap" style={{ textAlign: "center" }}>
<div data-r="" className="km-mr" style={{ fontSize: "22px", color: "#5A7A3A", marginBottom: "20px" }}>तुमच्या शेतासाठी दुसरी नजर</div>
<h2 data-r="" className="km-serif" style={{ margin: "0 auto", fontSize: "clamp(48px, 7vw, 112px)", lineHeight: ".95", fontWeight: "400", maxWidth: "1100px", transitionDelay: ".1s" }}>A second pair of eyes on <em style={{ color: "#5A7A3A" }}>your field</em></h2>
<p data-r="" style={{ margin: "34px auto 0", fontSize: "19px", lineHeight: "1.65", color: "#3F4D42", maxWidth: "600px", transitionDelay: ".2s" }}>Start with a leaf close-up, or just ask. A question about weather or sowing needs no photo at all.</p>
<div data-r="" style={{ marginTop: "48px", display: "flex", gap: "16px", justifyContent: "center", flexWrap: "wrap", transitionDelay: ".3s" }}>
<a className="km-btn is-dark" href="/checks/new" style={{ background: "#2F4A36", color: "#F2EEE5", borderColor: "#2F4A36" }}><span>Check a leaf</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M4 12h16M14 6l6 6-6 6"></path></svg></a>
<a className="km-btn is-dark" href="/checks/new?mode=question"><span>Ask a question</span></a>
</div>
</div>
</section>


<footer style={{ background: "#2F4A36", padding: "110px 0 48px" }}>
<div className="km-wrap">
<a href="/expert" className="km-hover-zoom" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: "24px", textDecoration: "none", color: "#F2EEE5", paddingBottom: "56px", borderBottom: "1px solid rgba(242,238,229,.16)", flexWrap: "wrap" }}>
<div>
<div style={{ fontSize: "12px", letterSpacing: ".22em", textTransform: "uppercase", color: "#E2CF9F", marginBottom: "16px" }}>Next</div>
<div className="km-serif" style={{ fontSize: "clamp(48px, 7vw, 108px)", lineHeight: ".95" }}>Expert desk</div>
<div style={{ fontSize: "17px", color: "rgba(242,238,229,.72)", marginTop: "14px" }}>Review queue, case snapshots and orchestration metrics</div>
</div>
<span className="km-arrow" style={{ width: "84px", height: "84px" }}><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.3" aria-hidden="true"><path d="M4 12h16M14 6l6 6-6 6"></path></svg></span>
</a>
<div style={{ display: "flex", justifyContent: "space-between", gap: "20px", flexWrap: "wrap", paddingTop: "32px", fontSize: "13px", color: "rgba(242,238,229,.62)" }}>
<span>KrishiMitra · Crop-health assistant for Maharashtra</span>
<span>Weather: Open-Meteo forecast-model data, not IMD</span>
</div>
</div>
</footer>

</div>
  );
}
