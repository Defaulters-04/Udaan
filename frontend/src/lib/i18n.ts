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
  domain_guessLabel: string;
  domain_guessMatch: string;
  domain_guessMismatch: string;

  // Page 5 link to explorer
  seeYourOptions: string;

  // Page 6 Negotiation Explorer strings
  explorerTitle: string;
  demoData: string;
  explorerSubtitle: string;
  explorerErrorTitle: string;
  explorerErrorDesc: string;
  explorerWaitingTitle: string;
  explorerWaitingDesc: string;
  explorerWaitingBadge: string;
  explorerFooterNote: string;

  xAxisLabel: string;
  yAxisLabel: string;
  compromiseZoneLabel: string;
  bestTradeOffsLabel: string;
  bestOnBothLabel: string;
  sweetSpotLabel: string;
  zoomedChip: string;
  showFullRange: string;
  showZoomedRange: string;
  chartAriaLabel: string;
  gutterTitle: string;
  allDomainsFilter: string;
  clickToInspectHint: string;

  legendTopPick: string;
  legendFrontier: string;
  legendEstimated: string;
  legendNeedsPlan: string;
  legendCoverageNote: string;

  sliderLeftLabel: string;
  sliderRightLabel: string;
  sliderBalanceStudent: string;
  sliderBalanceFamily: string;
  sliderBalancePill: string;
  heroTopMatch: string;
  sliderAriaValue: string;
  sliderTopPickSentence: string;
  sliderTopPickSentenceNoViab: string;
  sliderDisagreementNote: string;
  sliderTopPickEstimated: string;
  winnerStripCaption: string;
  winnerStripEstimatedAsterisk: string;

  rankedListTitle: string;
  chipBestTradeOff: string;
  chipCompromiseZone: string;
  chipEstimatedFigures: string;
  showAllToggle: string;
  showTop10Toggle: string;
  topPickAnnounced: string;

  detailPanelTitle: string;
  closeDetail: string;
  scoreFit: string;
  scoreViability: string;
  scoreMarket: string;
  scoreBlend: string;
  rankAtPosition: string;
  yearsToIncome: string;
  yearsCount: string;
  familyConflictLabel: string;
  conflictScore: string;
  estimatedNoteTitle: string;
  coincidentGroupTitle: string;
  selectCareerFromGroup: string;

  needsPlanTitle: string;
  needsPlanIntro: string;
  notEnoughDataTitle: string;
  notEnoughDataIntro: string;
  gateCostSentence: string;
  gateAcademicSentence: string;
  remediesHeader: string;
  englishOnlyNote: string;
  neutralRemedyLine: string;
  emptyStateTitle: string;

  gap_verified_route_costs: string;
  gap_verified_entry_salary: string;
  gap_regional_hiring: string;
  gap_exam_pattern: string;
  gap_pathway_cost: string;
  gap_market_demand: string;
  gap_salary_benchmarks: string;

  // Page 7 Career detail strings
  backToExplorer: string;
  openCareer: string;
  careerNotFound: string;
  careerNotFoundDesc: string;
  careerWaitingTitle: string;
  careerWaitingDesc: string;
  careerErrorTitle: string;
  careerErrorDesc: string;
  demoDataLabel: string;
  demoToggleSparse: string;
  demoToggleFull: string;

  statusWorkable: string;
  statusNeedsPlan: string;
  statusNeedsAcademic: string;
  statusNotEnoughData: string;

  careerFitLabel: string;
  careerViabilityLabel: string;
  careerYearsToIncomeLabel: string;
  careerConflictLabel: string;

  routesTitle: string;
  bestRouteBadge: string;
  tuitionCost: string;
  livingCost: string;
  entranceCost: string;
  costStatusVerified: string;
  costStatusUnverified: string;
  noRoutesAvailable: string;

  salaryTitle: string;
  salaryMin: string;
  salaryMedian: string;
  salaryMax: string;
  perYear: string;
  sourceLabel: string;

  demandTitle: string;
  demandPositive: string;
  demandNeutral: string;
  demandNegative: string;

  examsTitle: string;
  noExamsListed: string;

  scholarshipsTitle: string;
  scholarshipsNotAvailable: string;
  officialLink: string;

  growthAreasTitle: string;
  growthAreasSubtitle: string;

  familyMoneyTitle: string;
  onlyYouSeeThis: string;
  loanNeedLabel: string;
  monthlyEmiLabel: string;
  perMonth: string;

  whatWouldHelpTitle: string;
  pathwayResearchPending: string;

  dataGapsFootnote: string;
  dataGapsNone: string;
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
    domain_guessLabel: "{parent}'s guess about {student}",
    domain_guessMatch: "{parent} thought {student} would pick {domain}, and {student} did.",
    domain_guessMismatch: "{parent} thought {student} would pick {domain}. {student} picked {list}.",

    // Page 5 link
    seeYourOptions: "See your options",

    // Page 6 Negotiation Explorer
    explorerTitle: "Negotiation Explorer",
    demoData: "Demo data",
    explorerSubtitle: "Find career paths balancing what {student} loves with what the family can afford.",
    explorerErrorTitle: "Something is off with the data. Please try again.",
    explorerErrorDesc: "Please refresh or try again later.",
    explorerWaitingTitle: "Preparing your options…",
    explorerWaitingDesc: "Both members have submitted. Calculating trade-offs, affordability, and the compromise zone…",
    explorerWaitingBadge: "Checking automatically…",
    explorerFooterNote: "This is a screening tool, not a diagnosis. Scores are estimates from the data snapshot; any rupee amount is illustrative.",

    xAxisLabel: "What the family can afford",
    yAxisLabel: "What {student} would love",
    compromiseZoneLabel: "Compromise zone",
    bestTradeOffsLabel: "Best trade-offs",
    bestOnBothLabel: "Best on both",
    sweetSpotLabel: "Sweet spot: High fit & affordability",
    zoomedChip: "Zoomed to {min}–{max}",
    showFullRange: "Show full 0–100",
    showZoomedRange: "Zoom in",
    chartAriaLabel: "Scatter chart comparing student fit versus family affordability for all careers",
    gutterTitle: "Needs a plan",
    allDomainsFilter: "All Domains",
    clickToInspectHint: "Click any dot or career row to inspect details",

    legendTopPick: "Top pick",
    legendFrontier: "Best trade-offs",
    legendEstimated: "Estimated figures",
    legendNeedsPlan: "Needs a plan",
    legendCoverageNote: "Verified data for {n} of {total} careers; the others use estimated defaults.",

    sliderLeftLabel: "What {student} would love",
    sliderRightLabel: "What the family can afford",
    sliderBalanceStudent: "{student}'s Passion",
    sliderBalanceFamily: "Family Affordability",
    sliderBalancePill: "{studentPct}% Student • {familyPct}% Family",
    heroTopMatch: "#1 Top Pick at this balance",
    sliderAriaValue: "Priority balance: {val}% family affordability",
    sliderTopPickSentence: "At this setting the top pick is {career}: fit {fit}, affordability {viability}.",
    sliderTopPickSentenceNoViab: "At this setting the top pick is {career}: fit {fit}.",
    sliderDisagreementNote: "Scores also lower careers the family disagrees about.",
    sliderTopPickEstimated: "This top pick rests on some estimated figures.",
    winnerStripCaption: "Who is the top pick as you move the slider",
    winnerStripEstimatedAsterisk: "* some figures estimated",

    rankedListTitle: "Ranked careers",
    chipBestTradeOff: "Best trade-off",
    chipCompromiseZone: "In the compromise zone",
    chipEstimatedFigures: "Estimated figures",
    showAllToggle: "Show all ({count})",
    showTop10Toggle: "Show top 10",
    topPickAnnounced: "Top pick changed to {career}, score {score}",

    detailPanelTitle: "Career details",
    closeDetail: "Close",
    scoreFit: "Student fit",
    scoreViability: "Family affordability",
    scoreMarket: "Job market",
    scoreBlend: "Score at current setting",
    rankAtPosition: "Rank #{rank}",
    yearsToIncome: "Years to first income",
    yearsCount: "{n} years",
    familyConflictLabel: "How far apart the family is on this career",
    conflictScore: "{score} / 100",
    estimatedNoteTitle: "Estimated figures",
    coincidentGroupTitle: "Careers at this point ({count})",
    selectCareerFromGroup: "Select a career to view details:",

    needsPlanTitle: "Needs a plan",
    needsPlanIntro: "Not out of reach: here is what would make it workable.",
    notEnoughDataTitle: "Not enough data yet",
    notEnoughDataIntro: "We don't have verified pathway and cost data for this career yet, so we can't say whether it's affordable.",
    gateCostSentence: "College fees and pathway costs currently exceed the family budget.",
    gateAcademicSentence: "Requires specific qualifying subjects or competitive entrance exam preparation.",
    remediesHeader: "What could help:",
    englishOnlyNote: "English only",
    neutralRemedyLine: "Explore government merit-cum-means scholarships and alternative regional colleges.",
    emptyStateTitle: "No career fits the budget you described yet. Here is what could change that.",

    gap_verified_route_costs: "Educational pathway & tuition fees",
    gap_verified_entry_salary: "Starting entry-level salary",
    gap_regional_hiring: "Regional hiring trends",
    gap_exam_pattern: "Entrance exam eligibility",
    gap_pathway_cost: "Course and pathway fees",
    gap_market_demand: "Job market demand",
    gap_salary_benchmarks: "Salary benchmarks",

    // Page 7 Career detail
    backToExplorer: "Back to options",
    openCareer: "Open career",
    careerNotFound: "Career not found",
    careerNotFoundDesc: "This career could not be found or has been removed.",
    careerWaitingTitle: "Waiting for family",
    careerWaitingDesc: "Both members must complete the questionnaire before exploring career details.",
    careerErrorTitle: "Could not load career details",
    careerErrorDesc: "Please check your connection and try again.",
    demoDataLabel: "Demo data",
    demoToggleSparse: "View sparse example",
    demoToggleFull: "View full example",

    statusWorkable: "Workable with your family's plan",
    statusNeedsPlan: "Needs a plan",
    statusNeedsAcademic: "Needs academic preparation",
    statusNotEnoughData: "Not enough data yet",

    careerFitLabel: "Student fit",
    careerViabilityLabel: "Family viability",
    careerYearsToIncomeLabel: "Years to first income",
    careerConflictLabel: "Conflict index",

    routesTitle: "Education pathways",
    bestRouteBadge: "Best route",
    tuitionCost: "Tuition",
    livingCost: "Living",
    entranceCost: "Entrance",
    costStatusVerified: "Verified",
    costStatusUnverified: "Unverified",
    noRoutesAvailable: "No educational pathways mapped yet.",

    salaryTitle: "Entry salary",
    salaryMin: "Min",
    salaryMedian: "Median",
    salaryMax: "Max",
    perYear: "per year",
    sourceLabel: "Source",

    demandTitle: "Market demand",
    demandPositive: "Positive outlook",
    demandNeutral: "Steady outlook",
    demandNegative: "Slowed hiring",

    examsTitle: "Entrance exams",
    noExamsListed: "No specific entrance exams listed.",

    scholarshipsTitle: "Scholarships",
    scholarshipsNotAvailable: "Scholarship data isn't available yet.",
    officialLink: "Official portal",

    growthAreasTitle: "Growth areas",
    growthAreasSubtitle: "Skill preparation based on your assessment answers.",

    familyMoneyTitle: "Family financing",
    onlyYouSeeThis: "Only you see this.",
    loanNeedLabel: "Estimated loan needed",
    monthlyEmiLabel: "Estimated monthly EMI",
    perMonth: "per month",

    whatWouldHelpTitle: "What would help",
    pathwayResearchPending: "Pathway research is pending for this career.",

    dataGapsFootnote: "Not available yet: {gaps}",
    dataGapsNone: "All data verified for this career.",
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
    domain_guessLabel: "{student} के बारे में {parent} का अनुमान",
    domain_guessMatch: "{parent} को लगा था कि {student} {domain} चुनेंगे, और {student} ने वही चुना।",
    domain_guessMismatch: "{parent} को लगा था कि {student} {domain} चुनेंगे। {student} ने {list} चुना।",

    // Page 5 link
    seeYourOptions: "अपने विकल्प देखें",

    // Page 6 Negotiation Explorer
    explorerTitle: "सहमति और करियर विकल्प",
    demoData: "डेमो डेटा",
    explorerSubtitle: "ऐसे करियर खोजें जो {student} की पसंद और परिवार के बजट दोनों में सही बैठें।",
    explorerErrorTitle: "डेटा में कुछ गड़बड़ी है। कृपया पुनः प्रयास करें।",
    explorerErrorDesc: "कृपया पेज को रीफ़्रेश करें या थोड़ी देर बाद प्रयास करें।",
    explorerWaitingTitle: "आपके करियर विकल्प तैयार हो रहे हैं…",
    explorerWaitingDesc: "दोनों सदस्यों ने फ़ॉर्म सबमिट कर दिया है। सर्वोत्तम विकल्प, बजट और सहमति क्षेत्र का हिसाब लगाया जा रहा है…",
    explorerWaitingBadge: "स्वचालित रूप से जाँच हो रही है…",
    explorerFooterNote: "यह केवल एक आरंभिक आकलन है, कोई अंतिम निदान नहीं। सभी अंक डेटा के आधार पर अनुमानित हैं और राशियाँ केवल समझाने के लिए हैं।",

    xAxisLabel: "परिवार की सामर्थ्य (बजट)",
    yAxisLabel: "{student} की पसंद",
    compromiseZoneLabel: "सहमति क्षेत्र",
    bestTradeOffsLabel: "सर्वश्रेष्ठ संतुलन",
    bestOnBothLabel: "दोनों में सबसे आगे",
    sweetSpotLabel: "सर्वोत्तम क्षेत्र: उच्च पसंद और बजट",
    zoomedChip: "{min}–{max} पर ज़ूम किया गया",
    showFullRange: "पूरा 0–100 देखें",
    showZoomedRange: "ज़ूम इन करें",
    chartAriaLabel: "करियर की पसंद और परिवार के बजट की तुलना करने वाला चार्ट",
    gutterTitle: "योजना ज़रूरी है",
    allDomainsFilter: "सभी क्षेत्र",
    clickToInspectHint: "विस्तृत जानकारी देखने के लिए किसी भी बिंदु या पंक्ति पर क्लिक करें",

    legendTopPick: "शीर्ष पसंद",
    legendFrontier: "सर्वश्रेष्ठ संतुलन",
    legendEstimated: "अनुमानित आँकड़े",
    legendNeedsPlan: "योजना ज़रूरी है",
    legendCoverageNote: "{total} में से {n} करियर के लिए प्रमाणित डेटा उपलब्ध है; बाक़ी अनुमानित मानकों पर आधारित हैं।",

    sliderLeftLabel: "{student} की पसंद",
    sliderRightLabel: "परिवार का बजट",
    sliderBalanceStudent: "{student} की पसंद",
    sliderBalanceFamily: "परिवार की सामर्थ्य",
    sliderBalancePill: "{studentPct}% विद्यार्थी • {familyPct}% परिवार",
    heroTopMatch: "इस संतुलन पर #1 शीर्ष पसंद",
    sliderAriaValue: "प्राथमिकता: {val}% परिवार की सामर्थ्य",
    sliderTopPickSentence: "इस स्थिति पर शीर्ष पसंद {career} है: पसंद {fit}, सामर्थ्य {viability}।",
    sliderTopPickSentenceNoViab: "इस स्थिति पर शीर्ष पसंद {career} है: पसंद {fit}।",
    sliderDisagreementNote: "जिन करियर पर परिवार में मतभेद है, उनके अंक भी कम हो जाते हैं।",
    sliderTopPickEstimated: "यह शीर्ष पसंद कुछ अनुमानित आँकड़ों पर आधारित है।",
    winnerStripCaption: "जैसे-जैसे आप स्लाइडर खिसकाएँगे, शीर्ष पसंद बदलती दिखेगी",
    winnerStripEstimatedAsterisk: "* कुछ आँकड़े अनुमानित हैं",

    rankedListTitle: "वरीयता सूची",
    chipBestTradeOff: "सर्वश्रेष्ठ संतुलन",
    chipCompromiseZone: "सहमति क्षेत्र में",
    chipEstimatedFigures: "अनुमानित आँकड़े",
    showAllToggle: "सभी ({count}) देखें",
    showTop10Toggle: "शीर्ष 10 देखें",
    topPickAnnounced: "शीर्ष पसंद बदलकर {career} हो गई, अंक {score}",

    detailPanelTitle: "करियर का विवरण",
    closeDetail: "बंद करें",
    scoreFit: "विद्यार्थी की पसंद",
    scoreViability: "परिवार की सामर्थ्य",
    scoreMarket: "रोज़गार बाज़ार",
    scoreBlend: "वर्तमान स्थिति पर अंक",
    rankAtPosition: "रैंक #{rank}",
    yearsToIncome: "कमाई शुरू होने में वर्ष",
    yearsCount: "{n} वर्ष",
    familyConflictLabel: "इस करियर को लेकर परिवार में असहमति",
    conflictScore: "{score} / 100",
    estimatedNoteTitle: "अनुमानित आँकड़े",
    coincidentGroupTitle: "इस बिंदु पर करियर ({count})",
    selectCareerFromGroup: "विवरण देखने के लिए करियर चुनें:",

    needsPlanTitle: "योजना की ज़रूरत है",
    needsPlanIntro: "यह असंभव नहीं है: इसे संभव बनाने के रास्ते यहाँ दिए गए हैं।",
    notEnoughDataTitle: "पर्याप्त डेटा अभी उपलब्ध नहीं",
    notEnoughDataIntro: "हमारे पास अभी इस करियर के लिए प्रमाणित मार्ग और लागत का डेटा नहीं है, इसलिए हम यह नहीं कह सकते कि यह बजट में है या नहीं।",
    gateCostSentence: "कॉलेज की फ़ीस और कुल ख़र्च वर्तमान में परिवार के बजट से अधिक है।",
    gateAcademicSentence: "इसके लिए विशिष्ट विषयों या प्रतियोगी प्रवेश परीक्षा की तैयारी आवश्यक है।",
    remediesHeader: "मददगार उपाय:",
    englishOnlyNote: "केवल अंग्रेज़ी में",
    neutralRemedyLine: "सरकारी छात्रवृत्ति योजनाओं और क्षेत्रीय कॉलेजों के विकल्पों की पड़ताल करें।",
    emptyStateTitle: "आपके बताए गए बजट में अभी कोई करियर पूरी तरह फिट नहीं बैठता। इसे बदलने के विकल्प नीचे दिए गए हैं।",

    gap_verified_route_costs: "कॉलेज की फ़ीस और कुल ख़र्च",
    gap_verified_entry_salary: "शुरुआती वेतन",
    gap_regional_hiring: "क्षेत्रीय नौकरियों के रुझान",
    gap_exam_pattern: "प्रवेश परीक्षा के नियम",
    gap_pathway_cost: "कोर्स व कॉलेज की फ़ीस",
    gap_market_demand: "नौकरियों की मांग",
    gap_salary_benchmarks: "वेतन के मानक",

    // Page 7 Career detail
    backToExplorer: "विकल्पों पर वापस",
    openCareer: "करियर देखें",
    careerNotFound: "करियर नहीं मिला",
    careerNotFoundDesc: "यह करियर नहीं मिला या हटा दिया गया है।",
    careerWaitingTitle: "परिवार का इंतज़ार है",
    careerWaitingDesc: "करियर की जानकारी देखने से पहले दोनों सदस्यों का प्रश्नावली पूरा करना आवश्यक है।",
    careerErrorTitle: "करियर की जानकारी लोड नहीं हो सकी",
    careerErrorDesc: "कृपया अपना कनेक्शन जांचें और दोबारा कोशिश करें।",
    demoDataLabel: "डेमो डेटा",
    demoToggleSparse: "अपूर्ण डेटा उदाहरण देखें",
    demoToggleFull: "पूर्ण डेटा उदाहरण देखें",

    statusWorkable: "आपके परिवार की योजना के अनुसार संभव",
    statusNeedsPlan: "एक योजना की आवश्यकता है",
    statusNeedsAcademic: "अकादमिक तैयारी की आवश्यकता है",
    statusNotEnoughData: "अभी पर्याप्त डेटा नहीं है",

    careerFitLabel: "विद्यार्थी की पसंद",
    careerViabilityLabel: "परिवार की क्षमता",
    careerYearsToIncomeLabel: "कमाई शुरू होने में साल",
    careerConflictLabel: "सहमति अंतर",

    routesTitle: "शिक्षा के रास्ते",
    bestRouteBadge: "सबसे उपयुक्त रास्ता",
    tuitionCost: "ट्यूशन फ़ीस",
    livingCost: "रहने का ख़र्च",
    entranceCost: "प्रवेश परीक्षा",
    costStatusVerified: "सत्यापित",
    costStatusUnverified: "अनुमानित",
    noRoutesAvailable: "अभी कोई मार्ग दर्ज नहीं है।",

    salaryTitle: "शुरुआती वेतन",
    salaryMin: "न्यूनतम",
    salaryMedian: "औसत",
    salaryMax: "अधिकतम",
    perYear: "प्रति वर्ष",
    sourceLabel: "स्रोत",

    demandTitle: "मार्केट में मांग",
    demandPositive: "सकारात्मक रुझान",
    demandNeutral: "स्थिर रुझान",
    demandNegative: "धीमा रुझान",

    examsTitle: "प्रमुख प्रवेश परीक्षाएं",
    noExamsListed: "कोई विशिष्ट प्रवेश परीक्षा सूचीबद्ध नहीं है।",

    scholarshipsTitle: "छात्रवृत्तियां",
    scholarshipsNotAvailable: "छात्रवृत्ति डेटा अभी उपलब्ध नहीं है।",
    officialLink: "आधिकारिक पोर्टल",

    growthAreasTitle: "सुधार के क्षेत्र",
    growthAreasSubtitle: "आपके मूल्यांकन के आधार पर सुझाई गई तैयारी।",

    familyMoneyTitle: "परिवार का वित्तीय प्रबंधन",
    onlyYouSeeThis: "यह केवल आपको दिखाई देता है।",
    loanNeedLabel: "अनुमानित आवश्यक लोन",
    monthlyEmiLabel: "अनुमानित मासिक EMI",
    perMonth: "प्रति माह",

    whatWouldHelpTitle: "क्या मदद कर सकता है",
    pathwayResearchPending: "इस करियर के लिए मार्ग अनुसंधान अभी लंबित है।",

    dataGapsFootnote: "अभी यह डेटा उपलब्ध नहीं है: {gaps}",
    dataGapsNone: "इस करियर के लिए सभी आवश्यक डेटा उपलब्ध है।",
  },
};

export type TranslationKey = keyof Translations;

export function getTranslation(lang: Language): Translations {
  return translations[lang] || translations.en;
}
