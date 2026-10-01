/**
 * English UI copy. This file is the SOURCE OF TRUTH for message keys: Marathi (mr.ts) must have exactly the same keys,
 * and the compiler enforces it.
 *
 * Rules for this copy:
 * - Image-based answers are always "preliminary", never a "confirmed diagnosis".
 * - KrishiMitra never gives pesticide names or doses, and no string here may contain one.
 * - Copy is built from the API's structured fields (state, reason_code, confidence_band, ...). The backend's English
 *   `message` and `follow_up_question` are never shown to users.
 * - Use {name} placeholders; the Marathi string must use the same placeholders.
 */
export const en = {
  // ------------------------------------------------------------------ app, common, language
  "app.name": "KrishiMitra",
  "common.signOut": "Sign out",
  "common.tryAgain": "Try again",
  "common.back": "Back",
  "common.loading": "Loading…",
  "language.label": "Language",
  "language.choose": "Choose language",
  "role.farmer": "Farmer",
  "role.expert": "Expert",

  // ------------------------------------------------------------------ shells
  "shell.nav.reviewQueue": "Review queue",
  "shell.nav.metrics": "Metrics",
  "shell.nav.main": "Main navigation",
  "shell.badge.expert": "Expert",
  "shell.skipToContent": "Skip to content",
  "shell.account": "Account",

  // ------------------------------------------------------------------ auth
  "auth.hero.title": "Check your soybean crop from a photo.",
  "auth.hero.subtitle": "Sign in to see your crop checks and any answers from an agriculture expert.",
  "auth.signUp.title": "Create your account",
  "auth.signUp.subtitle": "One account keeps all your crop checks and expert answers together.",
  "auth.tab.signIn": "Sign in",
  "auth.tab.signUp": "Create account",
  "auth.tabs.label": "Sign in or create an account",
  "auth.field.email": "Email",
  "auth.field.password": "Password",
  "auth.field.emailPlaceholder": "you@example.com",
  "auth.field.passwordPlaceholder": "At least {min} characters",
  "auth.submit.signIn": "Sign in",
  "auth.submit.signUp": "Create account",
  "auth.submitting.signIn": "Signing in…",
  "auth.submitting.signUp": "Creating your account…",
  "auth.signUp.note": "We'll email you a link to confirm your address before your first check.",
  "auth.footer.disclaimer": "Answers are preliminary guidance, never a confirmed diagnosis.",
  "auth.footer.sessionExpired":
    "Signed out because your session expired? Sign in again to continue where you left off.",
  "auth.validation.emailRequired": "Enter your email address.",
  "auth.validation.emailInvalid": "That doesn't look like an email address.",
  "auth.validation.passwordRequired": "Enter your password.",
  "auth.validation.passwordShort": "Use at least {min} characters.",
  "auth.error.invalid.title": "Email or password is wrong",
  "auth.error.invalid.body": "Check both and try again. Passwords are case-sensitive.",
  "auth.error.unconfirmed.title": "Confirm your email first",
  "auth.error.unconfirmed.body": "We sent you a confirmation link. Open it, then sign in.",
  "auth.error.rateLimit.title": "Too many attempts",
  "auth.error.rateLimit.body": "Wait a minute, then try again.",
  "auth.error.weakPassword.title": "That password is too weak",
  "auth.error.weakPassword.body": "Use at least {min} characters, and avoid common words.",
  "auth.error.network.title": "Couldn't reach the sign-in service",
  "auth.error.network.body": "Check your internet connection and try again.",
  "auth.error.notConfigured.title": "Sign-in isn't set up yet",
  "auth.error.notConfigured.body": "This app is missing its Supabase settings. See .env.local.example.",
  "auth.error.confirmLink.title": "That confirmation link didn't work",
  "auth.error.confirmLink.body": "It may have expired. Sign in, or create your account again.",
  "auth.error.generic.title": "Something went wrong",
  "auth.error.generic.body": "Please try again.",
  "auth.checkEmail.title": "Check your email",
  "auth.checkEmail.body": "We sent a confirmation link to {email}. Open it to finish creating your account.",
  "auth.checkEmail.back": "Back to sign in",

  // ------------------------------------------------------------------ 403 page (neutral shell, never the expert shell)
  "forbidden.expert.title": "This account can't open the review queue",
  "forbidden.expert.body":
    "The queue is only for agriculture experts. If you've just been given expert access, sign out and sign in again so your account picks it up.",
  "forbidden.expert.hint": "Still blocked? Ask an admin to confirm your account has the expert role.",
  "forbidden.generic.title": "You don't have access to this page",
  "forbidden.generic.body": "Your account isn't allowed to open this page.",
  "forbidden.signOutAgain": "Sign out and sign in again",
  "forbidden.tryAgain": "Try again",
  "forbidden.checking": "Checking your account…",
  "forbidden.stillBlocked": "Your account still doesn't have expert access.",
  "forbidden.home": "Go to my home page",
  "forbidden.code": "403 · Expert role required",

  // ------------------------------------------------------------------ temporary landing pages (real session info only)
  "placeholder.farmer.title": "Your crop checks",
  "placeholder.expert.title": "Review queue",
  "placeholder.notBuilt": "This screen isn't built yet.",
  "placeholder.signedInAs": "Signed in as {email}",
  "placeholder.role": "Role: {role}",

  // ------------------------------------------------------------------ API errors, by ApiError.code
  "error.network": "Couldn't reach KrishiMitra. Check your internet connection.",
  "error.timeout": "This is taking too long. Try again.",
  "error.unauthorized": "Your session has expired. Sign in again.",
  "error.forbidden": "You don't have permission to do that.",
  "error.notFound": "We couldn't find that.",
  "error.conflict": "That has already been done.",
  "error.tooLarge": "That file is larger than 10 MB.",
  "error.unsupportedMedia": "Send a JPEG, PNG or WebP photo.",
  "error.invalid": "Some of what you entered isn't valid.",
  "error.unavailable": "The service isn't available right now. Try again soon.",
  "error.server": "Something went wrong on our side. Try again.",
  "error.unknown": "Something went wrong. Try again.",

  // ------------------------------------------------------------------ decision states (state)
  "state.NEEDS_BETTER_IMAGE.label": "Needs a better photo",
  "state.NEEDS_BETTER_IMAGE.badge": "Needs photo",
  "state.NEEDS_BETTER_IMAGE.summary": "We need a clearer close-up photo before we can say anything.",
  "state.NEEDS_MORE_CONTEXT.label": "Needs more information",
  "state.NEEDS_MORE_CONTEXT.badge": "Needs info",
  "state.NEEDS_MORE_CONTEXT.summary": "We need a little more information to go on.",
  "state.PRELIMINARY_GUIDANCE.label": "Preliminary guidance",
  "state.PRELIMINARY_GUIDANCE.badge": "Guidance ready",
  "state.PRELIMINARY_GUIDANCE.summary": "Here is what we can say so far. It is preliminary.",
  "state.EXPERT_REVIEW.label": "With an expert",
  "state.EXPERT_REVIEW.badge": "With an expert",
  "state.EXPERT_REVIEW.summary": "A human agriculture expert will look at this.",
  "state.UNSUPPORTED.label": "Not supported",
  "state.UNSUPPORTED.badge": "Not supported",
  "state.UNSUPPORTED.summary": "KrishiMitra can't help with this yet.",

  // ------------------------------------------------------------------ reason codes (reason_code, reason_detail)
  "reason.quality_failed.title": "The photo can't be used yet",
  "reason.quality_failed.body": "Please upload a clearer, well-lit close-up photo of a single affected leaf. {tip}",
  "reason.crop_not_soybean.title": "KrishiMitra supports soybean only",
  "reason.crop_not_soybean.body": "Other crops aren't supported yet.",
  "reason.farmer_requested_expert.title": "Sent to an expert",
  "reason.farmer_requested_expert.body":
    "You asked to talk to an expert, so a human agriculture expert will pick this up.",
  "reason.unsupported_request.title": "We can't help with that here",
  "reason.unsupported_request.body":
    "KrishiMitra helps with soybean crop health. For other crops, loans, prices or schemes, please contact your local agriculture office.",
  "reason.intent_unclear.title": "We need to understand your question",
  "reason.intent_unclear.body": "Please tell us a little more, or add a close-up photo of an affected leaf.",
  "reason.treatment_needs_expert.title": "A question for an expert",
  "reason.treatment_needs_expert.body":
    "KrishiMitra does not give pesticide names or doses. We don't have a verified source for this, so an agriculture expert will look at your question. Until then, talk to your local Krishi Vigyan Kendra or agriculture officer before spraying anything.",
  "reason.treatment_verified_source.title": "Where to read about this",
  "reason.treatment_verified_source.body":
    "KrishiMitra does not give pesticide names or doses. Please read the source below, follow the product label, and confirm with your agriculture officer before applying anything.",
  "reason.weather_context.title": "Weather for {district}",
  "reason.weather_context.body": "Weather information is indicative. Check local forecasts before field work.",
  "reason.advisory_lookup.title": "From the advisory",
  "reason.advisory_lookup.body": "This is general information. Confirm with your local agriculture officer.",
  "reason.general_crop_question.title": "General guidance",
  "reason.general_crop_question.body": "This is general information. Confirm with your local agriculture officer.",
  "reason.low_confidence_request_evidence.title": "We can't tell from this photo",
  "reason.low_confidence_request_evidence.body":
    "A photo of the wider field would help. This is a preliminary observation, not a confirmed diagnosis.",
  "reason.low_confidence_escalate.title": "Sent to an expert",
  "reason.low_confidence_escalate.body":
    "We aren't confident enough to say anything about this, so an agriculture expert will review it.",
  "reason.models_conflict.title": "Sent to an expert",
  "reason.models_conflict.body": "Our checks disagree with each other, so an agriculture expert will review it.",
  "reason.label_unknown.title": "Sent to an expert",
  "reason.label_unknown.body":
    "We couldn't match this to a condition we know, so an agriculture expert will review it.",
  "reason.mid_confidence.title": "Possible, not certain",
  "reason.mid_confidence.body":
    "We can share general information and ask one question. No treatment is suggested at this level of confidence.",
  "reason.high_confidence.title": "Looks consistent with the photo",
  "reason.high_confidence.body":
    "This is a preliminary observation, not a confirmed diagnosis. Please confirm with your local agriculture officer before taking any action.",
  "reason.sources_unavailable.title": "We couldn't back this up with a verified source",
  "reason.sources_unavailable.advisory":
    "No verified advisory is available for this yet, so an agriculture expert will review it.",
  "reason.sources_unavailable.weather": "Current weather isn't available, so an agriculture expert will review it.",
  "reason.sources_unavailable.vision_error":
    "We couldn't read your photo automatically, so an agriculture expert will review it.",
  "reason.sources_unavailable.quality_gate_error":
    "We couldn't check your photo automatically, so an agriculture expert will review it.",
  "reason.sources_unavailable.intent_router_error":
    "We couldn't understand your question automatically, so an agriculture expert will review it.",
  "reason.sources_unavailable.unknown":
    "A needed source wasn't available, so an agriculture expert will review it.",

  // ------------------------------------------------------------------ photo quality (reason_detail, next_action)
  "quality.issue.missing_image": "No photo was received.",
  "quality.issue.unreadable_image": "The file couldn't be opened as a photo. Send a JPEG, PNG or WebP.",
  "quality.issue.too_small": "The photo is too small. Move closer so the leaf fills most of the frame.",
  "quality.issue.too_dark": "The photo is too dark. Take it in daylight.",
  "quality.issue.too_bright": "The photo is overexposed. Avoid direct glare or shade the leaf.",
  "quality.issue.blurry": "The photo is blurry. Hold the phone steady and tap the leaf to focus.",
  "quality.issue.no_leaf_detected": "We couldn't find a leaf. Fill most of the frame with one soybean leaf.",
  "quality.action.continue": "Continue",
  "quality.action.upload_image": "Add a close-up photo",
  "quality.action.retake_closer": "Retake closer",
  "quality.action.retake_in_daylight": "Retake in daylight",
  "quality.action.retake_avoid_glare": "Retake without glare",
  "quality.action.retake_steady": "Retake, holding steady",
  "quality.action.retake_leaf_in_frame": "Retake with the leaf in frame",

  // ------------------------------------------------------------------ confidence bands (confidence_band)
  "band.label": "Confidence",
  "band.aria": "Confidence: {band}",
  "band.low.label": "Low",
  "band.medium.label": "Medium",
  "band.high.label": "High",
  "band.low.range": "Low · under {low}",
  "band.low.explain":
    "At low confidence we don't name a condition. We ask for more evidence or send it to an expert.",
  "band.medium.explain":
    "At medium confidence we share general information and ask one question. No treatment is suggested.",
  "band.high.explain": "At high confidence we add weather and advisory information. It is still preliminary.",

  // ------------------------------------------------------------------ missing information (missing_information[])
  "missing.close_up_photo.title": "A close-up photo",
  "missing.close_up_photo.hint": "One sharp photo of an affected leaf, taken in daylight.",
  "missing.clearer_close_up_photo.title": "A clearer photo",
  "missing.clearer_close_up_photo.hint": "Retake it in daylight, holding the phone steady.",
  "missing.symptom_description.title": "What you see on the plant",
  "missing.symptom_description.hint": "For example spots, yellowing or holes.",
  "missing.affected_leaf_position.title": "Which leaves show the spots",
  "missing.affected_leaf_position.hint": "Older, younger or both. Answer in Next step.",
  "missing.verified_advisory_source.title": "A verified advisory",
  "missing.verified_advisory_source.hint": "No verified source exists for this yet.",
  "missing.current_weather.title": "Current weather",
  "missing.current_weather.hint": "Weather couldn't be loaded.",
  "missing.treatment_source.title": "A verified treatment source",
  "missing.treatment_source.hint": "KrishiMitra never gives pesticide names or doses.",
  "missing.field_overview_photo.title": "Field photo",
  "missing.field_overview_photo.hint": "Optional. Shows how widely it has spread.",
  "missing.growth_stage.title": "Growth stage",
  "missing.growth_stage.hint": "Optional. For example R3.",
  "missing.symptom_start_date.title": "When it started",
  "missing.symptom_start_date.hint": "Optional. The date you first noticed it.",
  "missing.recent_rainfall.title": "Recent rain",
  "missing.recent_rainfall.hint": "Optional. None, light or heavy.",

  // ------------------------------------------------------------------ follow-up questions (follow_up_options)
  "followUp.question.leaf_position": "Are the symptoms on older leaves, younger leaves, or both?",
  "followUp.question.field_overview_photo": "Can you add a photo of the wider field showing how the plants look?",
  "followUp.question.describe_problem": "What do you see on the plant, or what would you like to know?",
  "followUp.option.older_leaves": "Older leaves",
  "followUp.option.younger_leaves": "Younger leaves",
  "followUp.option.both": "Both",

  // ------------------------------------------------------------------ possible condition (preliminary_label) and safety
  "category.healthy": "Healthy-looking leaf",
  "category.rust_like": "Rust-like signs",
  "category.leaf_spot_like": "Leaf-spot-like signs",
  "category.insect_damage": "Signs of insect damage",
  "category.unknown": "We can't tell what this is",
  "safety.preliminary": "This is a preliminary observation, not a confirmed diagnosis.",
  "safety.noteTitle": "Safety note",
  "safety.note":
    "KrishiMitra never gives pesticide names or doses. Before spraying anything, talk to your local Krishi Vigyan Kendra or agriculture officer.",
  "safety.unavailable":
    "Until you see a result, don't spray anything based on a guess. Your local Krishi Vigyan Kendra can advise.",

  // ------------------------------------------------------------------ the recorded trace (trace[])
  "trace.step.intent_router": "Understand the question",
  "trace.step.quality_gate": "Check photo quality",
  "trace.step.vision": "Read the leaf",
  "trace.step.advisory": "Find guidance",
  "trace.step.weather": "Weather",
  "trace.step.policy_decision": "Apply safety rules",
  "trace.status.completed": "Done",
  "trace.status.failed": "Failed",
  "trace.status.skipped": "Skipped",
  "trace.skipped.route_does_not_use_step": "Not needed for this kind of question",
  "trace.skipped.stopped_earlier": "Skipped because an earlier step ended the check",
  "trace.skipped.confidence_not_high": "Only used when the leaf reading is high confidence",
  "trace.latency": "{ms} ms",

  // ------------------------------------------------------------------ routes (path)
  "route.label": "Route",
  "route.image_diagnosis": "A crop-health question with a photo, so we check the photo before reading it.",
  "route.weather": "A weather question, so we only look up the weather.",
  "route.treatment_safety":
    "A pesticide question. We never give names or doses, so we look for a verified source or ask an expert.",
  "route.advisory_lookup": "A question about official advice, so we look it up in the advisories.",
  "route.general_crop_question": "A general soybean question, so we look for general guidance.",
  "route.expert_escalation": "You asked for an expert, so we send this straight to one.",
  "route.unsupported_request": "This isn't about soybean crop health, so we can't help with it here.",
  "route.none": "No route was needed.",

  // ------------------------------------------------------------------ sources and weather provenance
  "source.verified": "Verified",
  "source.demo": "Demo source, not verified",
  "source.upToDate": "Up to date",
  "source.stale": "Out of date",
  "source.structured": "Structured record",
  "source.generalText": "General text",
  "source.published": "Published {date}",
  "source.retrieved": "Retrieved {date}",
  "source.publisher": "Publisher: {name}",
  "source.noneVerified": "No verified source found.",
  "weather.source.live": "Live",
  "weather.source.cached": "Saved reading",
  "weather.source.demo": "Demo data",
  "weather.source.unavailable": "Unavailable",
  "weather.source.stale": "Old reading",
  "weather.provenance.live": "{provider} forecast-model data (live), for {when}",
  "weather.provenance.cached": "{provider} data cached from {when} (not live)",
  "weather.provenance.cachedStale": "{provider} data cached from {when} (not live, out of date)",
  "weather.provenance.demo": "DEMO data for testing only, not a real forecast",
  "weather.provenance.unavailable": "No weather data available",
  "weather.staleNote":
    "Live weather isn't responding. This reading is more than {hours} hours old, so it isn't used in your crop advice.",

  // ------------------------------------------------------------------ expert workflow
  "expert.status.pending_review": "Pending review",
  "expert.status.awaiting_farmer": "Awaiting farmer",
  "expert.status.reviewed": "Reviewed",
  "expert.status.follow_up_received": "Follow-up received",
  "expert.decision.likely": "Likely condition",
  "expert.decision.likely.hint": "Pick a category. Still not a lab-confirmed diagnosis.",
  "expert.decision.insufficient": "Not enough evidence",
  "expert.decision.insufficient.hint": "Nothing can be said from what was sent.",
  "expert.decision.unknown": "Can't identify",
  "expert.decision.unknown.hint": "You don't recognise what this is.",
  "expert.decision.request_more": "Ask the farmer for more",
  "expert.decision.request_more.hint": "Notes required: say what to send.",
  "expert.tag.treatment_needs_expert": "Treatment question",
  "expert.tag.farmer_requested_expert": "Farmer asked for expert",
  "expert.tag.low_confidence_escalate": "Low photo confidence",
  "expert.tag.models_conflict": "Checks disagree",
  "expert.tag.label_unknown": "Unknown condition",
  "expert.tag.sources_unavailable": "No verified source",
  "expert.tag.other": "Needs review",
  "image.kind.leaf_closeup": "Close-up photo",
  "image.kind.field_overview": "Field photo",
} as const satisfies Record<string, string>;

export type MessageKey = keyof typeof en;
