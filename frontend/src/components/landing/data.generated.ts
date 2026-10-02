// Copied verbatim from the Claude Design landing export. Do not edit by hand.
export const RAW_STEPS: { step: string; model: string; note: string; ms: string; skip?: boolean }[] = [
      { step: 'intent_router', model: 'keyword-intent-rules', note: 'Matched “yellow”, “spot”, “leaves”: crop health, with photo', ms: '0 ms' },
      { step: 'quality_gate', model: 'opencv-quality-gate', note: 'Score 100 / 100. Sharp, well lit, leaf in frame', ms: '30 ms' },
      { step: 'vision', model: 'mobilenetv3-onnx', note: 'rust_like at 0.65: medium confidence', ms: '34 ms' },
      { step: 'advisory', model: 'placeholder-advisory', note: '1 source found, shown as unverified demo data', ms: '0 ms' },
      { step: 'weather', model: 'weather-adapter', note: 'Skipped: only fetched above 0.85 confidence', ms: 'skipped', skip: true },
      { step: 'policy_decision', model: 'policy-engine', note: 'PRELIMINARY_GUIDANCE, plus one follow-up question', ms: '0 ms' }
    ];

export const INTENTS: { num: string; q: string; route: string; what: string; photo: string; state: string }[] = [
        { num: '01', q: 'Yellow spots on the leaves', route: 'image_diagnosis', what: 'Photo check, then the vision model, then an advisory lookup. Weather joins only when confidence is high.', photo: 'Needs a photo', state: 'Preliminary guidance' },
        { num: '02', q: 'Will it rain in my area?', route: 'weather', what: 'Your district’s forecast with its source and time, labelled live, cached or demo.', photo: 'No photo needed', state: 'Preliminary guidance' },
        { num: '03', q: 'Latest KVK crop advisory', route: 'advisory_lookup', what: 'Looks up advisory sources and tells you whether each one is verified.', photo: 'No photo needed', state: 'Guidance or expert' },
        { num: '04', q: 'When should I sow?', route: 'general_crop_question', what: 'General crop guidance from advisory sources. If the question is unclear, it asks you to describe the problem.', photo: 'No photo needed', state: 'Guidance or follow-up' },
        { num: '05', q: 'Which pesticide and how much?', route: 'treatment_safety', what: 'Never a name or a dose. Without a verified source, it goes straight to a human expert.', photo: 'No photo needed', state: 'Expert review' },
        { num: '06', q: 'I want to talk to an expert', route: 'expert_escalation', what: 'Opens an expert case right away, with your question and photos attached.', photo: 'No photo needed', state: 'Expert review' },
        { num: '07', q: 'My cotton leaves have spots', route: 'unsupported_request', what: 'Other crops, loans, prices and schemes are out of scope, and it says so plainly.', photo: 'No photo needed', state: 'Unsupported' }
      ];

export const STATES: { num: string; title: string; code: string; text: string }[] = [
        { num: '01', title: 'Needs a better image', code: 'NEEDS_BETTER_IMAGE', text: 'The photo was too dark, blurry, small or missing the leaf. You get one specific tip, like “retake steady”, and try again.' },
        { num: '02', title: 'Needs more context', code: 'NEEDS_MORE_CONTEXT', text: 'Not enough to go on yet. You are asked one question, or for a photo of the wider field.' },
        { num: '03', title: 'Preliminary guidance', code: 'PRELIMINARY_GUIDANCE', text: 'An answer, with its confidence band and sources. Image answers stay preliminary and never include a treatment.' },
        { num: '04', title: 'Expert review', code: 'EXPERT_REVIEW', text: 'A human agriculture expert takes the case. You can see their status and notes as they review it.' },
        { num: '05', title: 'Unsupported', code: 'UNSUPPORTED', text: 'Another crop, or a request like loans or market prices. Clearly said, never guessed.' }
      ];
