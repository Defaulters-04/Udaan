export type Language = 'en' | 'hi';

export interface Translations {
  tagline: string;
  roleQuestion: string;
  student: string;
  parent: string;
  nameQuestion: string;
  namePlaceholder: string;
  continue: string;
  greeting: string;
  langQuestion: string;
  begin: string;
  change: string;
  consent: string;
  page2Next: string;
  page2Desc: string;
  backToWelcome: string;
  savedRole: string;
  savedName: string;
  savedLang: string;
  emptyStoreWarning: string;
  langToggleAria: string;
  stepAriaAnnouncement: string;

  // Page 2 & invite strings
  linkTitle: string;
  instrToParent: string;
  instrToStudent: string;
  codeLabel: string;
  copyCode: string;
  copied: string;
  waiting: string;
  partnerParent: string;
  partnerStudent: string;
  haveCode: string;
  codePlaceholder: string;
  join: string;
  connected: string;
  privacyNote: string;
  invited: string;
  errNotFound: string;
  errRoleTaken: string;
  errFull: string;
  errNetwork: string;
  startNormally: string;
  page3Next: string;
  page4Next: string;
  joining: string;

  // Page 3 Assessment strings
  questionOf: string;
  back: string;
  skip: string;
  required: string;
  saving: string;
  saved: string;
  saveFailed: string;
  sectionDone: string;
  nextUp: string;
  reviewTitle: string;
  reviewBody: string;
  backToReview: string;
  edit: string;
  submit: string;
  submitting: string;
  doneTitle: string;
  waitingParentDone: string;
  bothDone: string;
  compare: string;
  loadFailed: string;
  retry: string;
  page5Next: string;
  answeredOf: string;

  // Page 4 Intake strings
  intakeReviewTitle: string;
  intakeReviewBody: string;
  confirmSubmit: string;
  skippedAnswer: string;
  maxSelectHint: string;
  privacyIntake: string;
  waitingStudentDone: string;

  // Page 5 Mirror strings
  mirrorTitle: string;
  mirrorSubtitle: string;
  gaugeOutOf100: string;
  gaugeCaption: string;
  gaugeAria: string;
  diffPercent: string;
  weightPercent: string;
  chipStudent: string;
  chipParent: string;
  chipBoth: string;
  mirrorWaitingTitle: string;
  mirrorWaitingDesc: string;
  mirrorWaitingBadge: string;
  mirrorErrorTitle: string;
  mirrorErrorDesc: string;
  mirrorFooterNote: string;

  // Scale dimension titles
  dim_risk: string;
  dim_domain: string;
  dim_relocation: string;
  dim_time: string;

  // Scale templates
  risk_same: string;
  risk_studentHigher: string;
  risk_parentHigher: string;
  relocation_same: string;
  relocation_studentHigher: string;
  relocation_parentHigher: string;
  time_same: string;
  time_studentHigher: string;
  time_parentHigher: string;
  scale_same: string;
  scale_studentHigher: string;
  scale_parentHigher: string;

  // Picks templates
  domain_shared: string;
  domain_none: string;
  domain_guessMatch: string;
  domain_guessMismatch: string;
}

export const translations: Record<Language, Translations> = {
  en: {
    tagline: "Careers your whole family can agree on.",
    roleQuestion: "Who's here?",
    student: "I'm a student",
    parent: "I'm a parent",
    nameQuestion: "What should we call you?",
    namePlaceholder: "First name",
    continue: "Continue",
    greeting: "Nice to meet you, {name}.",
    langQuestion: "Which language is easier for you?",
    begin: "Let's begin",
    change: "Change",
    consent: "This is a guidance tool, not a diagnosis. Money details stay in this session only.",
    page2Next: "Page 2 comes next",
    page2Desc: "Page 2: Link the family (coming soon)",
    backToWelcome: "Back to Welcome",
    savedRole: "Role",
    savedName: "Name",
    savedLang: "Language",
    emptyStoreWarning: "No saved session found in this tab.",
    langToggleAria: "Switch language between English and Hindi",
    stepAriaAnnouncement: "Step updated",

    // Page 2 & invite
    linkTitle: "Link your family",
    instrToParent: "Ask your parent to scan this QR code, or enter the code below on their own device.",
    instrToStudent: "Ask your child to scan this QR code, or enter the code below on their own device.",
    codeLabel: "Your family code",
    copyCode: "Copy code",
    copied: "Copied",
    waiting: "Waiting for your {partner} to join…",
    partnerParent: "parent",
    partnerStudent: "student",
    haveCode: "Already have a code?",
    codePlaceholder: "Enter 6-character code",
    join: "Join",
    connected: "Connected with {name}.",
    privacyNote: "Your answers stay private until you both finish.",
    invited: "{name} invited you to Udaan.",
    errNotFound: "We couldn't find that code. Check it and try again.",
    errRoleTaken: "That family already has someone in your role. Check the code.",
    errFull: "That family is already linked.",
    errNetwork: "Can't reach the server. Check your connection and try again.",
    startNormally: "Start without a code",
    page3Next: "Page 3 comes next",
    page4Next: "Page 4 comes next",
    joining: "Joining…",

    // Page 3 Assessment
    questionOf: "{n} of {total}",
    back: "Back",
    skip: "Skip",
    required: "Please answer this to continue.",
    saving: "Saving…",
    saved: "Saved",
    saveFailed: "Couldn't save. Retrying…",
    sectionDone: "{section} done.",
    nextUp: "Next: {section}",
    reviewTitle: "Almost done",
    reviewBody: "Check your answers, then submit. You can change any of them.",
    backToReview: "Back to review",
    edit: "Edit",
    submit: "Submit",
    submitting: "Submitting…",
    doneTitle: "Thanks, {name}. You're done.",
    waitingParentDone: "Waiting for your parent to finish…",
    bothDone: "You're both done.",
    compare: "Compare answers",
    loadFailed: "Couldn't load the questions.",
    retry: "Try again",
    page5Next: "Page 5 comes next",
    answeredOf: "{answered} of {total}",

    // Page 4 Intake
    intakeReviewTitle: "Please check your answers",
    intakeReviewBody: "These are the answers we'll use. Change anything that isn't right, then confirm.",
    confirmSubmit: "Confirm and submit",
    skippedAnswer: "Skipped",
    maxSelectHint: "Choose up to {n}.",
    privacyIntake: "Your exact money answers are never shown to your child.",
    waitingStudentDone: "Waiting for your child to finish…",

    // Page 5 Mirror
    mirrorTitle: "Family Mirror",
    mirrorSubtitle: "Where your answers align and where you see things differently.",
    gaugeOutOf100: "out of 100",
    gaugeCaption: "How far apart the two sets of answers are, averaged across the areas below.",
    gaugeAria: "Conflict index: {score} out of 100",
    diffPercent: "Difference: {n}%",
    weightPercent: "Counts for {n}% of the score",
    chipStudent: "Student",
    chipParent: "Parent",
    chipBoth: "Both",
    mirrorWaitingTitle: "Waiting for {partner} to finish…",
    mirrorWaitingDesc: "Your answers are saved. Once {partner} submits, your Family Mirror will appear here automatically.",
    mirrorWaitingBadge: "Checking automatically…",
    mirrorErrorTitle: "Couldn't load Family Mirror",
    mirrorErrorDesc: "Please check your connection and try again.",
    mirrorFooterNote: "This is a screening tool, not a diagnosis. The job-offer amounts are illustrative.",

    dim_risk: "Risk tolerance",
    dim_domain: "Career areas of interest",
    dim_relocation: "Relocation willingness",
    dim_time: "Time before earning",

    risk_same: "{student} and {parent} have the same comfort with risk.",
    risk_studentHigher: "{student} is more comfortable taking risks than {parent}.",
    risk_parentHigher: "{parent} is more comfortable taking risks than {student}.",

    relocation_same: "{student} and {parent} agree on relocation distance.",
    relocation_studentHigher: "{student} is more open to moving far than {parent}.",
    relocation_parentHigher: "{parent} is more open to moving far than {student}.",

    time_same: "{student} and {parent} agree on the time to start earning.",
    time_studentHigher: "{student} is okay waiting longer to start earning than {parent}.",
    time_parentHigher: "{parent} is okay waiting longer to start earning than {student}.",

    scale_same: "{student} and {parent} are on the same step.",
    scale_studentHigher: "{student} is on a higher step than {parent}.",
    scale_parentHigher: "{parent} is on a higher step than {student}.",

    domain_shared: "{student} and {parent} both picked {domains}.",
    domain_none: "No domain appears in both lists.",
    domain_guessMatch: "{parent} guessed {domain}, which is one of {student}'s picks.",
    domain_guessMismatch: "{parent} guessed {domain}; {student} picked {list}.",
  },
  hi: {
    tagline: "ऐसा करियर, जिस पर पूरा परिवार सहमत हो।",
    roleQuestion: "आप कौन हैं?",
    student: "मैं विद्यार्थी हूँ",
    parent: "मैं अभिभावक हूँ",
    nameQuestion: "हम आपको किस नाम से बुलाएँ?",
    namePlaceholder: "आपका पहला नाम",
    continue: "आगे बढ़ें",
    greeting: "आपसे मिलकर अच्छा लगा, {name}।",
    langQuestion: "आपके लिए कौन-सी भाषा आसान है?",
    begin: "शुरू करें",
    change: "बदलें",
    consent: "यह मार्गदर्शन का टूल है, कोई निदान नहीं। पैसों की जानकारी सिर्फ़ इसी सेशन में रहती है।",
    page2Next: "पेज 2 आगे आएगा",
    page2Desc: "पेज 2: परिवार को लिंक करें (जल्द आ रहा है)",
    backToWelcome: "शुरुआत पर वापस जाएँ",
    savedRole: "भूमिका",
    savedName: "नाम",
    savedLang: "भाषा",
    emptyStoreWarning: "इस टैब में कोई सहेजी गई जानकारी नहीं मिली।",
    langToggleAria: "अंग्रेजी और हिन्दी के बीच भाषा बदलें",
    stepAriaAnnouncement: "चरण अपडेट हुआ",

    // Page 2 & invite
    linkTitle: "अपने परिवार को जोड़ें",
    instrToParent: "अपने अभिभावक से कहें कि वे इस QR कोड को स्कैन करें, या अपने डिवाइस पर नीचे दिया कोड डालें।",
    instrToStudent: "अपने बच्चे से कहें कि वे इस QR कोड को स्कैन करें, या अपने डिवाइस पर नीचे दिया कोड डालें।",
    codeLabel: "आपका फ़ैमिली कोड",
    copyCode: "कोड कॉपी करें",
    copied: "कॉपी हो गया",
    waiting: "आपके {partner} के जुड़ने का इंतज़ार है…",
    partnerParent: "अभिभावक",
    partnerStudent: "विद्यार्थी",
    haveCode: "पहले से कोड है?",
    codePlaceholder: "6 अक्षरों का कोड डालें",
    join: "जुड़ें",
    connected: "{name} से जुड़ गए।",
    privacyNote: "आप दोनों के पूरा करने तक आपके जवाब निजी रहते हैं।",
    invited: "{name} ने आपको Udaan पर बुलाया है।",
    errNotFound: "यह कोड नहीं मिला। जाँचकर दोबारा कोशिश करें।",
    errRoleTaken: "इस परिवार में आपकी भूमिका में कोई पहले से जुड़ा है। कोड जाँचें।",
    errFull: "यह परिवार पहले से जुड़ चुका है।",
    errNetwork: "सर्वर से संपर्क नहीं हो पा रहा। कनेक्शन जाँचकर दोबारा कोशिश करें।",
    startNormally: "बिना कोड के शुरू करें",
    page3Next: "पेज 3 आगे आएगा",
    page4Next: "पेज 4 आगे आएगा",
    joining: "जुड़ रहे हैं…",

    // Page 3 Assessment
    questionOf: "{n} / {total}",
    back: "वापस",
    skip: "छोड़ें",
    required: "आगे बढ़ने के लिए इसका जवाब दें।",
    saving: "सेव हो रहा है…",
    saved: "सेव हो गया",
    saveFailed: "सेव नहीं हो पाया। दोबारा कोशिश हो रही है…",
    sectionDone: "{section} पूरा हुआ।",
    nextUp: "आगे: {section}",
    reviewTitle: "बस थोड़ा और",
    reviewBody: "अपने जवाब देख लें, फिर सबमिट करें। आप कोई भी जवाब बदल सकते हैं।",
    backToReview: "समीक्षा पर वापस जाएं",
    edit: "बदलें",
    submit: "सबमिट करें",
    submitting: "सबमिट हो रहा है…",
    doneTitle: "धन्यवाद {name}। आपका हिस्सा पूरा हुआ।",
    waitingParentDone: "आपके अभिभावक के पूरा करने का इंतज़ार है…",
    bothDone: "आप दोनों का हिस्सा पूरा हुआ।",
    compare: "जवाब मिलाकर देखें",
    loadFailed: "प्रश्न लोड नहीं हो पाए।",
    retry: "फिर कोशिश करें",
    page5Next: "पेज 5 आगे आएगा",
    answeredOf: "{answered} / {total}",

    // Page 4 Intake
    intakeReviewTitle: "कृपया अपने जवाब जाँच लें",
    intakeReviewBody: "यही जवाब इस्तेमाल होंगे। जो सही न हो उसे बदलें, फिर पक्का करें।",
    confirmSubmit: "पक्का करें और सबमिट करें",
    skippedAnswer: "छोड़ा गया",
    maxSelectHint: "ज़्यादा से ज़्यादा {n} चुनें।",
    privacyIntake: "पैसों से जुड़े आपके सटीक जवाब आपके बच्चे को कभी नहीं दिखाए जाते।",
    waitingStudentDone: "आपके बच्चे के पूरा करने का इंतज़ार है…",

    // Page 5 Mirror
    mirrorTitle: "फ़ैमिली मिरर",
    mirrorSubtitle: "जानिए कहाँ आपके विचार मिलते हैं और कहाँ आपकी सोच में फ़र्क है।",
    gaugeOutOf100: "100 में से",
    gaugeCaption: "नीचे दिए गए सभी क्षेत्रों के आधार पर दोनों के विचारों में कुल अंतर का औसत।",
    gaugeAria: "कॉन्फ्लिक्ट इंडेक्स: 100 में से {score}",
    diffPercent: "अंतर: {n}%",
    weightPercent: "स्कोर में {n}% महत्व",
    chipStudent: "विद्यार्थी",
    chipParent: "अभिभावक",
    chipBoth: "दोनों",
    mirrorWaitingTitle: "{partner} के पूरा करने का इंतज़ार है…",
    mirrorWaitingDesc: "आपके जवाब सहेजे जा चुके हैं। {partner} के सबमिट करते ही फ़ैमिली मिरर यहाँ अपने आप दिखने लगेगा।",
    mirrorWaitingBadge: "स्वचालित रूप से जाँच हो रही है…",
    mirrorErrorTitle: "फ़ैमिली मिरर लोड नहीं हो पाया",
    mirrorErrorDesc: "कृपया अपना इंटरनेट कनेक्शन जाँचें और दोबारा कोशिश करें।",
    mirrorFooterNote: "यह केवल एक आरंभिक आकलन है, कोई अंतिम निदान नहीं। नौकरी के प्रस्तावों की राशियाँ केवल समझाने के लिए अनुमानित हैं।",

    dim_risk: "जोखिम उठाने की क्षमता",
    dim_domain: "पसंदीदा करियर क्षेत्र",
    dim_relocation: "बाहर जाने की इच्छा",
    dim_time: "कमाई शुरू करने का समय",

    risk_same: "{student} और {parent} दोनों का जोखिम उठाने का नज़रिया एक जैसा है।",
    risk_studentHigher: "{student}, {parent} की तुलना में जोखिम उठाने में ज़्यादा सहज है।",
    risk_parentHigher: "{parent}, {student} की तुलना में जोखिम उठाने में ज़्यादा सहज है।",

    relocation_same: "{student} और {parent} दोनों बाहर जाने की दूरी पर सहमत हैं।",
    relocation_studentHigher: "{student}, {parent} की तुलना में दूर जाने के लिए ज़्यादा तैयार है।",
    relocation_parentHigher: "{parent}, {student} की तुलना में दूर जाने के लिए ज़्यादा तैयार है।",

    time_same: "{student} और {parent} दोनों कमाई शुरू करने के समय पर सहमत हैं।",
    time_studentHigher: "{student}, {parent} की तुलना में कमाई शुरू करने के लिए लंबा इंतज़ार करने को तैयार है।",
    time_parentHigher: "{parent}, {student} की तुलना में कमाई शुरू करने के लिए लंबा इंतज़ार करने को तैयार है।",

    scale_same: "{student} और {parent} एक ही पायदान पर हैं।",
    scale_studentHigher: "{student}, {parent} से आगे के पायदान पर है।",
    scale_parentHigher: "{parent}, {student} से आगे के पायदान पर है।",

    domain_shared: "{student} और {parent} दोनों ने {domains} चुना है।",
    domain_none: "दोनों की पसंद में कोई भी क्षेत्र समान नहीं है।",
    domain_guessMatch: "{parent} ने {domain} का अनुमान लगाया था, और यह {student} की पसंद में शामिल है।",
    domain_guessMismatch: "{parent} ने {domain} का अनुमान लगाया था; {student} ने {list} चुना।",
  },
};

export type TranslationKey = keyof Translations;

export function getTranslation(lang: Language): Translations {
  return translations[lang] || translations.en;
}
