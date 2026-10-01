/**
 * Marathi UI copy: DRAFT. NEEDS NATIVE REVIEW.
 *
 * Every string in this file was drafted by a non-native speaker and has NOT been reviewed. Do not treat any of it
 * as final. Specifically check, with a Marathi-speaking farmer or agriculture officer:
 *   - the safety strings (safety.*, *.treatment_*, "preliminary / not a confirmed diagnosis"), where the NEGATION must survive;
 *   - agricultural terms (तांबेरा for rust, पानांवरील ठिपके for leaf spot, कृषी विज्ञान केंद्र for KVK, मात्रा for dose);
 *   - register: this draft uses the polite imperative (करा, टाका) throughout;
 *   - digits: these strings use Western digits (0-9) in numbers; decide whether to use Devanagari digits (०-९).
 *
 * Keys and {placeholders} must match en.ts exactly (the compiler and the tests enforce it).
 * When a string has been reviewed, add its key to REVIEWED_KEYS in ../review.ts.
 * `npm run i18n:review` regenerates src/i18n/MARATHI_REVIEW.md, the sheet to hand to the reviewer.
 */
import type { MessageKey } from "./en";

export const mr: Record<MessageKey, string> = {
  // ------------------------------------------------------------------ app, common, language
  "app.name": "KrishiMitra",
  "common.signOut": "लॉग आउट",
  "common.tryAgain": "पुन्हा प्रयत्न करा",
  "common.back": "मागे",
  "common.loading": "लोड होत आहे…",
  "language.label": "भाषा",
  "language.choose": "भाषा निवडा",
  "role.farmer": "शेतकरी",
  "role.expert": "तज्ञ",

  // ------------------------------------------------------------------ shells
  "shell.nav.reviewQueue": "पुनरावलोकन रांग",
  "shell.nav.metrics": "मेट्रिक्स",
  "shell.nav.main": "मुख्य मार्गदर्शक",
  "shell.badge.expert": "तज्ञ",
  "shell.skipToContent": "मुख्य मजकुराकडे जा",
  "shell.account": "खाते",

  // ------------------------------------------------------------------ auth
  "auth.hero.title": "फोटोवरून तुमच्या सोयाबीन पिकाची तपासणी करा.",
  "auth.hero.subtitle": "तुमच्या पीक तपासण्या आणि कृषी तज्ञांची उत्तरे पाहण्यासाठी लॉग इन करा.",
  "auth.signUp.title": "तुमचे खाते तयार करा",
  "auth.signUp.subtitle": "एकाच खात्यात तुमच्या सर्व पीक तपासण्या आणि तज्ञांची उत्तरे एकत्र राहतात.",
  "auth.tab.signIn": "लॉग इन",
  "auth.tab.signUp": "खाते तयार करा",
  "auth.tabs.label": "लॉग इन करा किंवा खाते तयार करा",
  "auth.field.email": "ईमेल",
  "auth.field.password": "पासवर्ड",
  "auth.field.emailPlaceholder": "you@example.com",
  "auth.field.passwordPlaceholder": "किमान {min} अक्षरे",
  "auth.submit.signIn": "लॉग इन",
  "auth.submit.signUp": "खाते तयार करा",
  "auth.submitting.signIn": "लॉग इन होत आहे…",
  "auth.submitting.signUp": "खाते तयार होत आहे…",
  "auth.signUp.note": "तुमची पहिली तपासणी करण्यापूर्वी पत्ता पक्का करण्यासाठी आम्ही तुम्हाला एक लिंक ईमेल करू.",
  "auth.footer.disclaimer": "ही उत्तरे प्राथमिक मार्गदर्शन आहेत; ती कधीही निश्चित निदान नाहीत.",
  "auth.footer.sessionExpired":
    "सत्र संपल्यामुळे बाहेर पडलात का? जिथे थांबला होतात तिथून पुढे जाण्यासाठी पुन्हा लॉग इन करा.",
  "auth.validation.emailRequired": "तुमचा ईमेल पत्ता टाका.",
  "auth.validation.emailInvalid": "हा ईमेल पत्त्यासारखा दिसत नाही.",
  "auth.validation.passwordRequired": "तुमचा पासवर्ड टाका.",
  "auth.validation.passwordShort": "किमान {min} अक्षरे वापरा.",
  "auth.error.invalid.title": "ईमेल किंवा पासवर्ड चुकीचा आहे",
  "auth.error.invalid.body": "दोन्ही तपासा आणि पुन्हा प्रयत्न करा. पासवर्डमध्ये लहान-मोठ्या अक्षरांचा फरक पडतो.",
  "auth.error.unconfirmed.title": "आधी तुमचा ईमेल पक्का करा",
  "auth.error.unconfirmed.body": "आम्ही तुम्हाला पक्का करण्यासाठी लिंक पाठवली आहे. ती उघडा आणि मग लॉग इन करा.",
  "auth.error.rateLimit.title": "खूप वेळा प्रयत्न झाले",
  "auth.error.rateLimit.body": "थोडा वेळ थांबा आणि पुन्हा प्रयत्न करा.",
  "auth.error.weakPassword.title": "हा पासवर्ड खूप कमकुवत आहे",
  "auth.error.weakPassword.body": "किमान {min} अक्षरे वापरा आणि सामान्य शब्द टाळा.",
  "auth.error.network.title": "लॉग इन सेवेशी संपर्क होऊ शकला नाही",
  "auth.error.network.body": "तुमचे इंटरनेट कनेक्शन तपासा आणि पुन्हा प्रयत्न करा.",
  "auth.error.notConfigured.title": "लॉग इन अजून सेट केलेले नाही",
  "auth.error.notConfigured.body": "या अॅपला Supabase ची सेटिंग्ज मिळालेली नाहीत. .env.local.example पहा.",
  "auth.error.confirmLink.title": "ती पक्का करण्याची लिंक चालली नाही",
  "auth.error.confirmLink.body": "ती कदाचित कालबाह्य झाली असेल. लॉग इन करा किंवा पुन्हा खाते तयार करा.",
  "auth.error.generic.title": "काहीतरी चुकले",
  "auth.error.generic.body": "कृपया पुन्हा प्रयत्न करा.",
  "auth.checkEmail.title": "तुमचा ईमेल तपासा",
  "auth.checkEmail.body": "आम्ही {email} वर पक्का करण्याची लिंक पाठवली आहे. खाते तयार करणे पूर्ण करण्यासाठी ती उघडा.",
  "auth.checkEmail.back": "लॉग इन कडे परत जा",

  // ------------------------------------------------------------------ 403 page
  "forbidden.expert.title": "या खात्याला पुनरावलोकन रांग उघडता येत नाही",
  "forbidden.expert.body":
    "ही रांग फक्त कृषी तज्ञांसाठी आहे. जर तुम्हाला आत्ताच तज्ञ प्रवेश मिळाला असेल, तर लॉग आउट करून पुन्हा लॉग इन करा, म्हणजे तुमच्या खात्याला तो मिळेल.",
  "forbidden.expert.hint": "अजूनही अडचण आहे? तुमच्या खात्याला तज्ञ भूमिका आहे का हे प्रशासकाकडून तपासून घ्या.",
  "forbidden.generic.title": "या पानावर जाण्याची तुम्हाला परवानगी नाही",
  "forbidden.generic.body": "तुमच्या खात्याला हे पान उघडण्याची परवानगी नाही.",
  "forbidden.signOutAgain": "लॉग आउट करा आणि पुन्हा लॉग इन करा",
  "forbidden.tryAgain": "पुन्हा प्रयत्न करा",
  "forbidden.checking": "तुमचे खाते तपासत आहे…",
  "forbidden.stillBlocked": "तुमच्या खात्याला अजूनही तज्ञ प्रवेश नाही.",
  "forbidden.home": "माझ्या मुख्य पानावर जा",
  "forbidden.code": "403 · तज्ञ भूमिका आवश्यक",

  // ------------------------------------------------------------------ temporary landing pages
  "placeholder.farmer.title": "तुमच्या पीक तपासण्या",
  "placeholder.expert.title": "पुनरावलोकन रांग",
  "placeholder.notBuilt": "हे पान अजून तयार झालेले नाही.",
  "placeholder.signedInAs": "{email} म्हणून लॉग इन केले",
  "placeholder.role": "भूमिका: {role}",

  // ------------------------------------------------------------------ API errors
  "error.network": "KrishiMitra शी संपर्क होऊ शकला नाही. तुमचे इंटरनेट कनेक्शन तपासा.",
  "error.timeout": "यास खूप वेळ लागत आहे. पुन्हा प्रयत्न करा.",
  "error.unauthorized": "तुमचे सत्र संपले आहे. पुन्हा लॉग इन करा.",
  "error.forbidden": "ते करण्याची तुम्हाला परवानगी नाही.",
  "error.notFound": "ते आम्हाला सापडले नाही.",
  "error.conflict": "ते आधीच झाले आहे.",
  "error.tooLarge": "ती फाइल 10 MB पेक्षा मोठी आहे.",
  "error.unsupportedMedia": "JPEG, PNG किंवा WebP फोटो पाठवा.",
  "error.invalid": "तुम्ही भरलेली काही माहिती योग्य नाही.",
  "error.unavailable": "सेवा सध्या उपलब्ध नाही. थोड्या वेळाने पुन्हा प्रयत्न करा.",
  "error.server": "आमच्या बाजूने काहीतरी चुकले. पुन्हा प्रयत्न करा.",
  "error.unknown": "काहीतरी चुकले. पुन्हा प्रयत्न करा.",

  // ------------------------------------------------------------------ decision states
  "state.NEEDS_BETTER_IMAGE.label": "चांगला फोटो हवा",
  "state.NEEDS_BETTER_IMAGE.badge": "फोटो हवा",
  "state.NEEDS_BETTER_IMAGE.summary": "काहीही सांगण्यापूर्वी आम्हाला जवळून घेतलेला स्पष्ट फोटो हवा आहे.",
  "state.NEEDS_MORE_CONTEXT.label": "अधिक माहिती हवी",
  "state.NEEDS_MORE_CONTEXT.badge": "माहिती हवी",
  "state.NEEDS_MORE_CONTEXT.summary": "पुढे जाण्यासाठी आम्हाला थोडी अधिक माहिती हवी आहे.",
  "state.PRELIMINARY_GUIDANCE.label": "प्राथमिक मार्गदर्शन",
  "state.PRELIMINARY_GUIDANCE.badge": "मार्गदर्शन तयार",
  "state.PRELIMINARY_GUIDANCE.summary": "आतापर्यंत आम्ही हे सांगू शकतो. हे प्राथमिक आहे.",
  "state.EXPERT_REVIEW.label": "तज्ञांकडे",
  "state.EXPERT_REVIEW.badge": "तज्ञांकडे",
  "state.EXPERT_REVIEW.summary": "कृषी तज्ञ व्यक्ती हे पाहतील.",
  "state.UNSUPPORTED.label": "समर्थित नाही",
  "state.UNSUPPORTED.badge": "समर्थित नाही",
  "state.UNSUPPORTED.summary": "KrishiMitra अजून यात मदत करू शकत नाही.",

  // ------------------------------------------------------------------ reason codes
  "reason.quality_failed.title": "हा फोटो अजून वापरता येत नाही",
  "reason.quality_failed.body": "कृपया एका बाधित पानाचा स्पष्ट, चांगल्या प्रकाशातील जवळून घेतलेला फोटो पाठवा. {tip}",
  "reason.crop_not_soybean.title": "KrishiMitra फक्त सोयाबीनसाठी आहे",
  "reason.crop_not_soybean.body": "इतर पिके अजून समर्थित नाहीत.",
  "reason.farmer_requested_expert.title": "तज्ञांकडे पाठवले",
  "reason.farmer_requested_expert.body": "तुम्ही तज्ञांशी बोलण्यास सांगितले, म्हणून कृषी तज्ञ व्यक्ती हे हाताळतील.",
  "reason.unsupported_request.title": "यात आम्ही येथे मदत करू शकत नाही",
  "reason.unsupported_request.body":
    "KrishiMitra सोयाबीन पिकाच्या आरोग्यासाठी मदत करते. इतर पिके, कर्ज, भाव किंवा योजनांसाठी तुमच्या स्थानिक कृषी कार्यालयाशी संपर्क करा.",
  "reason.intent_unclear.title": "तुमचा प्रश्न समजून घेणे आवश्यक आहे",
  "reason.intent_unclear.body": "कृपया थोडे अधिक सांगा, किंवा बाधित पानाचा जवळून फोटो जोडा.",
  "reason.treatment_needs_expert.title": "तज्ञांसाठी प्रश्न",
  "reason.treatment_needs_expert.body":
    "KrishiMitra कधीही कीटकनाशकांची नावे किंवा मात्रा सांगत नाही. यासाठी आमच्याकडे पडताळलेला स्रोत नाही, म्हणून कृषी तज्ञ तुमचा प्रश्न पाहतील. तोपर्यंत काहीही फवारण्यापूर्वी तुमच्या स्थानिक कृषी विज्ञान केंद्राशी किंवा कृषी अधिकाऱ्याशी बोला.",
  "reason.treatment_verified_source.title": "याबद्दल कुठे वाचावे",
  "reason.treatment_verified_source.body":
    "KrishiMitra कधीही कीटकनाशकांची नावे किंवा मात्रा सांगत नाही. कृपया खालील स्रोत वाचा, उत्पादनावरील सूचना पाळा आणि काहीही वापरण्यापूर्वी तुमच्या कृषी अधिकाऱ्याकडून खात्री करून घ्या.",
  "reason.weather_context.title": "{district} चे हवामान",
  "reason.weather_context.body": "हवामानाची माहिती अंदाजे आहे. शेतातील कामापूर्वी स्थानिक अंदाज तपासा.",
  "reason.advisory_lookup.title": "सल्ल्यानुसार",
  "reason.advisory_lookup.body": "ही सामान्य माहिती आहे. तुमच्या स्थानिक कृषी अधिकाऱ्याकडून खात्री करून घ्या.",
  "reason.general_crop_question.title": "सामान्य मार्गदर्शन",
  "reason.general_crop_question.body": "ही सामान्य माहिती आहे. तुमच्या स्थानिक कृषी अधिकाऱ्याकडून खात्री करून घ्या.",
  "reason.low_confidence_request_evidence.title": "या फोटोवरून आम्हाला सांगता येत नाही",
  "reason.low_confidence_request_evidence.body":
    "शेताचा मोठा फोटो उपयोगी ठरेल. हे प्राथमिक निरीक्षण आहे, निश्चित निदान नाही.",
  "reason.low_confidence_escalate.title": "तज्ञांकडे पाठवले",
  "reason.low_confidence_escalate.body": "याबद्दल काही सांगण्याइतकी आमची खात्री नाही, म्हणून कृषी तज्ञ हे तपासतील.",
  "reason.models_conflict.title": "तज्ञांकडे पाठवले",
  "reason.models_conflict.body": "आमच्या तपासण्यांमध्ये मतभेद आहेत, म्हणून कृषी तज्ञ हे तपासतील.",
  "reason.label_unknown.title": "तज्ञांकडे पाठवले",
  "reason.label_unknown.body": "आम्हाला हे आमच्या ओळखीच्या कोणत्याही स्थितीशी जुळवता आले नाही, म्हणून कृषी तज्ञ हे तपासतील.",
  "reason.mid_confidence.title": "शक्य आहे, पण निश्चित नाही",
  "reason.mid_confidence.body":
    "आम्ही सामान्य माहिती देऊ शकतो आणि एक प्रश्न विचारू. या पातळीच्या खात्रीवर कोणताही उपचार सुचवला जात नाही.",
  "reason.high_confidence.title": "फोटोशी सुसंगत दिसते",
  "reason.high_confidence.body":
    "हे प्राथमिक निरीक्षण आहे, निश्चित निदान नाही. कोणतीही कृती करण्यापूर्वी तुमच्या स्थानिक कृषी अधिकाऱ्याकडून खात्री करून घ्या.",
  "reason.sources_unavailable.title": "आम्ही हे पडताळलेल्या स्रोताने पुष्टी करू शकलो नाही",
  "reason.sources_unavailable.advisory":
    "यासाठी अजून पडताळलेला सल्ला उपलब्ध नाही, म्हणून कृषी तज्ञ हे तपासतील.",
  "reason.sources_unavailable.weather": "सध्याचे हवामान उपलब्ध नाही, म्हणून कृषी तज्ञ हे तपासतील.",
  "reason.sources_unavailable.vision_error":
    "आम्हाला तुमचा फोटो आपोआप वाचता आला नाही, म्हणून कृषी तज्ञ हे तपासतील.",
  "reason.sources_unavailable.quality_gate_error":
    "आम्हाला तुमचा फोटो आपोआप तपासता आला नाही, म्हणून कृषी तज्ञ हे तपासतील.",
  "reason.sources_unavailable.intent_router_error":
    "आम्हाला तुमचा प्रश्न आपोआप समजला नाही, म्हणून कृषी तज्ञ हे तपासतील.",
  "reason.sources_unavailable.unknown": "आवश्यक स्रोत उपलब्ध नव्हता, म्हणून कृषी तज्ञ हे तपासतील.",

  // ------------------------------------------------------------------ photo quality
  "quality.issue.missing_image": "फोटो मिळाला नाही.",
  "quality.issue.unreadable_image": "ती फाइल फोटो म्हणून उघडता आली नाही. JPEG, PNG किंवा WebP पाठवा.",
  "quality.issue.too_small": "फोटो खूप लहान आहे. पान जवळपास संपूर्ण चौकट भरेल इतके जवळ जा.",
  "quality.issue.too_dark": "फोटो खूप अंधारा आहे. दिवसाच्या प्रकाशात काढा.",
  "quality.issue.too_bright": "फोटोत खूप प्रकाश आला आहे. थेट चकाकी टाळा किंवा पानावर सावली करा.",
  "quality.issue.blurry": "फोटो धूसर आहे. फोन स्थिर धरा आणि फोकससाठी पानावर टॅप करा.",
  "quality.issue.no_leaf_detected": "आम्हाला पान सापडले नाही. चौकटीचा बहुतेक भाग एका सोयाबीन पानाने भरा.",
  "quality.action.continue": "पुढे जा",
  "quality.action.upload_image": "जवळून फोटो जोडा",
  "quality.action.retake_closer": "जवळून पुन्हा काढा",
  "quality.action.retake_in_daylight": "दिवसाच्या प्रकाशात पुन्हा काढा",
  "quality.action.retake_avoid_glare": "चकाकीशिवाय पुन्हा काढा",
  "quality.action.retake_steady": "फोन स्थिर धरून पुन्हा काढा",
  "quality.action.retake_leaf_in_frame": "पान चौकटीत ठेवून पुन्हा काढा",

  // ------------------------------------------------------------------ confidence bands
  "band.label": "खात्रीची पातळी",
  "band.aria": "खात्रीची पातळी: {band}",
  "band.low.label": "कमी",
  "band.medium.label": "मध्यम",
  "band.high.label": "जास्त",
  "band.low.range": "कमी · {low} पेक्षा कमी",
  "band.low.explain": "कमी खात्रीवर आम्ही कोणतीही स्थिती सांगत नाही. आम्ही अधिक पुरावा मागतो किंवा तज्ञांकडे पाठवतो.",
  "band.medium.explain":
    "मध्यम खात्रीवर आम्ही सामान्य माहिती देतो आणि एक प्रश्न विचारतो. कोणताही उपचार सुचवला जात नाही.",
  "band.high.explain": "जास्त खात्रीवर आम्ही हवामान आणि सल्ल्याची माहिती जोडतो. तरीही हे प्राथमिकच आहे.",

  // ------------------------------------------------------------------ missing information
  "missing.close_up_photo.title": "जवळून घेतलेला फोटो",
  "missing.close_up_photo.hint": "बाधित पानाचा दिवसाच्या प्रकाशात घेतलेला एक स्पष्ट फोटो.",
  "missing.clearer_close_up_photo.title": "अधिक स्पष्ट फोटो",
  "missing.clearer_close_up_photo.hint": "दिवसाच्या प्रकाशात, फोन स्थिर धरून पुन्हा काढा.",
  "missing.symptom_description.title": "रोपावर तुम्हाला काय दिसते",
  "missing.symptom_description.hint": "उदा. डाग, पिवळेपणा किंवा छिद्रे.",
  "missing.affected_leaf_position.title": "कोणत्या पानांवर डाग दिसतात",
  "missing.affected_leaf_position.hint": "जुनी, नवीन किंवा दोन्ही. पुढील पायरीत उत्तर द्या.",
  "missing.verified_advisory_source.title": "पडताळलेला सल्ला",
  "missing.verified_advisory_source.hint": "यासाठी अजून पडताळलेला स्रोत उपलब्ध नाही.",
  "missing.current_weather.title": "सध्याचे हवामान",
  "missing.current_weather.hint": "हवामान लोड होऊ शकले नाही.",
  "missing.treatment_source.title": "पडताळलेला उपचार स्रोत",
  "missing.treatment_source.hint": "KrishiMitra कधीही कीटकनाशकांची नावे किंवा मात्रा सांगत नाही.",
  "missing.field_overview_photo.title": "शेताचा फोटो",
  "missing.field_overview_photo.hint": "ऐच्छिक. ते किती पसरले आहे हे दाखवते.",
  "missing.growth_stage.title": "वाढीची अवस्था",
  "missing.growth_stage.hint": "ऐच्छिक. उदा. R3.",
  "missing.symptom_start_date.title": "ते कधी सुरू झाले",
  "missing.symptom_start_date.hint": "ऐच्छिक. तुम्हाला ते पहिल्यांदा दिसले ती तारीख.",
  "missing.recent_rainfall.title": "अलीकडचा पाऊस",
  "missing.recent_rainfall.hint": "ऐच्छिक. नाही, हलका किंवा जोरदार.",

  // ------------------------------------------------------------------ follow-up questions
  "followUp.question.leaf_position": "लक्षणे जुन्या पानांवर आहेत, नवीन पानांवर की दोन्हीवर?",
  "followUp.question.field_overview_photo": "रोपे कशी दिसतात हे दाखवणारा शेताचा मोठा फोटो जोडू शकता का?",
  "followUp.question.describe_problem": "रोपावर तुम्हाला काय दिसते, किंवा तुम्हाला काय जाणून घ्यायचे आहे?",
  "followUp.option.older_leaves": "जुनी पाने",
  "followUp.option.younger_leaves": "नवीन पाने",
  "followUp.option.both": "दोन्ही",

  // ------------------------------------------------------------------ possible condition and safety
  "category.healthy": "निरोगी दिसणारे पान",
  "category.rust_like": "तांबेरासारखी लक्षणे",
  "category.leaf_spot_like": "पानांवरील ठिपक्यांसारखी लक्षणे",
  "category.insect_damage": "कीटकांमुळे झालेल्या नुकसानाची लक्षणे",
  "category.unknown": "हे काय आहे ते आम्हाला सांगता येत नाही",
  "safety.preliminary": "हे प्राथमिक निरीक्षण आहे, निश्चित निदान नाही.",
  "safety.noteTitle": "सुरक्षितता सूचना",
  "safety.note":
    "KrishiMitra कधीही कीटकनाशकांची नावे किंवा मात्रा सांगत नाही. काहीही फवारण्यापूर्वी तुमच्या स्थानिक कृषी विज्ञान केंद्राशी किंवा कृषी अधिकाऱ्याशी बोला.",
  "safety.unavailable":
    "निकाल दिसेपर्यंत अंदाजावरून काहीही फवारू नका. तुमचे स्थानिक कृषी विज्ञान केंद्र सल्ला देऊ शकते.",

  // ------------------------------------------------------------------ trace
  "trace.step.intent_router": "प्रश्न समजून घेणे",
  "trace.step.quality_gate": "फोटोची गुणवत्ता तपासणे",
  "trace.step.vision": "पान वाचणे",
  "trace.step.advisory": "मार्गदर्शन शोधणे",
  "trace.step.weather": "हवामान",
  "trace.step.policy_decision": "सुरक्षितता नियम लावणे",
  "trace.status.completed": "पूर्ण",
  "trace.status.failed": "अयशस्वी",
  "trace.status.skipped": "वगळले",
  "trace.skipped.route_does_not_use_step": "या प्रकारच्या प्रश्नासाठी आवश्यक नाही",
  "trace.skipped.stopped_earlier": "आधीच्या पायरीवर तपासणी थांबल्यामुळे वगळले",
  "trace.skipped.confidence_not_high": "पानाची खात्री जास्त असतानाच वापरले जाते",
  "trace.latency": "{ms} ms",

  // ------------------------------------------------------------------ routes
  "route.label": "मार्ग",
  "route.image_diagnosis": "फोटोसह पीक-आरोग्याचा प्रश्न आहे, म्हणून वाचण्यापूर्वी आम्ही फोटो तपासतो.",
  "route.weather": "हा हवामानाचा प्रश्न आहे, म्हणून आम्ही फक्त हवामान पाहतो.",
  "route.treatment_safety":
    "हा कीटकनाशकांबद्दलचा प्रश्न आहे. आम्ही नावे किंवा मात्रा देत नाही, म्हणून आम्ही पडताळलेला स्रोत शोधतो किंवा तज्ञांना विचारतो.",
  "route.advisory_lookup": "अधिकृत सल्ल्याबद्दलचा प्रश्न आहे, म्हणून आम्ही तो सल्ल्यांमध्ये शोधतो.",
  "route.general_crop_question": "सोयाबीनबद्दलचा सामान्य प्रश्न आहे, म्हणून आम्ही सामान्य मार्गदर्शन शोधतो.",
  "route.expert_escalation": "तुम्ही तज्ञ मागितले, म्हणून आम्ही हे थेट त्यांच्याकडे पाठवतो.",
  "route.unsupported_request": "हे सोयाबीन पिकाच्या आरोग्याबद्दल नाही, म्हणून येथे आम्ही मदत करू शकत नाही.",
  "route.none": "कोणताही मार्ग लागला नाही.",

  // ------------------------------------------------------------------ sources and weather provenance
  "source.verified": "पडताळलेला",
  "source.demo": "नमुना स्रोत, पडताळलेला नाही",
  "source.upToDate": "अद्ययावत",
  "source.stale": "जुना",
  "source.structured": "संरचित नोंद",
  "source.generalText": "सामान्य मजकूर",
  "source.published": "प्रकाशित {date}",
  "source.retrieved": "मिळवले {date}",
  "source.publisher": "प्रकाशक: {name}",
  "source.noneVerified": "पडताळलेला स्रोत सापडला नाही.",
  "weather.source.live": "थेट",
  "weather.source.cached": "जतन केलेली नोंद",
  "weather.source.demo": "नमुना माहिती",
  "weather.source.unavailable": "उपलब्ध नाही",
  "weather.source.stale": "जुनी नोंद",
  "weather.provenance.live": "{provider} अंदाज-प्रारूप माहिती (थेट), {when} साठी",
  "weather.provenance.cached": "{provider} माहिती {when} पासून जतन केलेली (थेट नाही)",
  "weather.provenance.cachedStale": "{provider} माहिती {when} पासून जतन केलेली (थेट नाही, जुनी)",
  "weather.provenance.demo": "फक्त चाचणीसाठी नमुना माहिती, खरा अंदाज नाही",
  "weather.provenance.unavailable": "हवामानाची माहिती उपलब्ध नाही",
  "weather.staleNote":
    "थेट हवामान उत्तर देत नाही. ही नोंद {hours} तासांपेक्षा जुनी आहे, म्हणून ती तुमच्या पीक सल्ल्यात वापरली जात नाही.",

  // ------------------------------------------------------------------ expert workflow
  "expert.status.pending_review": "पुनरावलोकन प्रलंबित",
  "expert.status.awaiting_farmer": "शेतकऱ्याच्या उत्तराची प्रतीक्षा",
  "expert.status.reviewed": "पुनरावलोकन झाले",
  "expert.status.follow_up_received": "पाठपुरावा उत्तर मिळाले",
  "expert.decision.likely": "संभाव्य स्थिती",
  "expert.decision.likely.hint": "वर्ग निवडा. हे अजूनही प्रयोगशाळेत पुष्टी झालेले निदान नाही.",
  "expert.decision.insufficient": "पुरेसा पुरावा नाही",
  "expert.decision.insufficient.hint": "पाठवलेल्या माहितीवरून काहीही सांगता येत नाही.",
  "expert.decision.unknown": "ओळखता येत नाही",
  "expert.decision.unknown.hint": "हे काय आहे हे तुम्हाला ओळखता येत नाही.",
  "expert.decision.request_more": "शेतकऱ्याकडे अधिक माहिती मागा",
  "expert.decision.request_more.hint": "नोंद आवश्यक: काय पाठवायचे ते सांगा.",
  "expert.tag.treatment_needs_expert": "उपचाराबद्दल प्रश्न",
  "expert.tag.farmer_requested_expert": "शेतकऱ्याने तज्ञ मागितले",
  "expert.tag.low_confidence_escalate": "फोटोची खात्री कमी",
  "expert.tag.models_conflict": "तपासण्यांमध्ये मतभेद",
  "expert.tag.label_unknown": "अज्ञात स्थिती",
  "expert.tag.sources_unavailable": "पडताळलेला स्रोत नाही",
  "expert.tag.other": "पुनरावलोकन आवश्यक",
  "image.kind.leaf_closeup": "जवळून घेतलेला फोटो",
  "image.kind.field_overview": "शेताचा फोटो",
};
