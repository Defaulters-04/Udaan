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
  },
};

export type TranslationKey = keyof Translations;

export function getTranslation(lang: Language): Translations {
  return translations[lang] || translations.en;
}
