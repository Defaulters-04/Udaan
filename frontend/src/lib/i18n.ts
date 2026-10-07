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
  },
};

export type TranslationKey = keyof Translations;

export function getTranslation(lang: Language): Translations {
  return translations[lang] || translations.en;
}
