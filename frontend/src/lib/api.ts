import type { Role } from '@/store/session';
import type { Language } from '@/lib/i18n';

export interface CreateFamilyPayload {
  role: Role;
  name: string;
  lang: Language;
}

export interface CreateFamilyResponse {
  family_code: string;
  member_token: string;
  role: Role;
  expires_at: string;
}

export interface PreviewFamilyResponse {
  family_code: string;
  open_role: Role | null;
  creator_name: string;
}

export interface JoinFamilyPayload {
  role: Role;
  name: string;
  lang: Language;
}

export interface JoinFamilyResponse {
  family_code: string;
  member_token: string;
  role: Role;
  partner: {
    role: Role;
    name: string;
  };
  expires_at: string;
}

export interface FamilyMemberStatus {
  role: Role;
  name: string;
  done?: boolean;
}

export interface FamilyStatusResponse {
  family_code: string;
  linked: boolean;
  you: FamilyMemberStatus;
  partner: FamilyMemberStatus | null;
  expires_at: string;
}

export interface ApiErrorShape {
  error: {
    code: string;
    message: string;
    missing?: string[];
  };
}

export class ApiError extends Error {
  code: string;
  status: number;
  missing?: string[];

  constructor(code: string, message: string, status: number = 400, missing?: string[]) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.missing = missing;
  }
}

// ==========================================
// Assessment Data Types
// ==========================================
export type QuestionType =
  | 'single_choice'
  | 'multi_choice'
  | 'scale'
  | 'slider'
  | 'text'
  | 'long_text';

export interface LocalizedText {
  en: string;
  hi?: string;
}

export interface QuestionOption {
  id: string;
  label: LocalizedText;
}

export interface AssessmentQuestion {
  id: string;
  section_id: string;
  type: QuestionType;
  prompt: LocalizedText;
  required?: boolean;
  options?: QuestionOption[];
  min?: number;
  max?: number;
  step?: number;
  min_label?: LocalizedText;
  max_label?: LocalizedText;
  max_length?: number;
  placeholder?: LocalizedText;
  max_select?: number;
}

export interface AssessmentSection {
  id: string;
  title: LocalizedText;
  description?: LocalizedText;
  questions: AssessmentQuestion[];
}

export interface AssessmentQuestionsResponse {
  version?: string;
  sections: AssessmentSection[];
}

export type AnswerValue = string | string[] | number;

export interface AssessmentProgressResponse {
  answers: Record<string, AnswerValue>;
  submitted: boolean;
}

export interface SaveAnswersPayload {
  answers: Record<string, AnswerValue>;
}

export interface SaveAnswersResponse {
  answered?: number;
  total?: number;
  saved?: boolean;
  answers?: Record<string, AnswerValue>;
}

export interface SubmitAssessmentResponse {
  submitted: boolean;
  done?: boolean;
}

// ==========================================
// Mirror (Page 5: Family Comparison) Types
// ==========================================
export interface MirrorStep {
  id: string;
  label: LocalizedText;
}

export interface MirrorOption {
  id: string;
  label: LocalizedText;
}

export interface MirrorDimensionBase {
  id: 'risk' | 'domain' | 'relocation' | 'time' | string;
  gap: number;
  weight: number;
  kind: 'scale' | 'picks';
}

export interface MirrorScaleDimension extends MirrorDimensionBase {
  kind: 'scale';
  steps: MirrorStep[];
  student_step: number;
  parent_step: number;
}

export interface MirrorPicksDimension extends MirrorDimensionBase {
  kind: 'picks';
  options: MirrorOption[];
  student_picks: string[];
  parent_picks: string[];
  parent_guess: string | null;
}

export type MirrorDimension = MirrorScaleDimension | MirrorPicksDimension;

export interface MirrorResponse {
  conflict_index: number;
  dimensions: MirrorDimension[];
}

const getApiBaseUrl = (): string => {
  return process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
};

const isMockEnabled = (): boolean => {
  return process.env.NEXT_PUBLIC_USE_MOCK === 'true';
};

// ==========================================
// Mock Storage Helper
// ==========================================
interface MockFamilyRecord {
  code: string;
  creatorRole: Role;
  creatorName: string;
  creatorLang: Language;
  createdAt: number;
  joinedRole?: Role;
  joinedName?: string;
  studentSubmitted?: boolean;
  parentSubmitted?: boolean;
  studentSubmittedAt?: number;
  parentSubmittedAt?: number;
}

const inMemoryMockFamilies: Record<string, MockFamilyRecord> = {};
const inMemoryMockProgress: Record<string, AssessmentProgressResponse> = {};

const getMockFamilies = (): Record<string, MockFamilyRecord> => {
  if (typeof window !== 'undefined' && typeof sessionStorage !== 'undefined') {
    try {
      const raw = sessionStorage.getItem('udaan_mock_families');
      if (raw) return JSON.parse(raw);
    } catch {
      // fallback
    }
  }
  return inMemoryMockFamilies;
};

const saveMockFamily = (rec: MockFamilyRecord) => {
  inMemoryMockFamilies[rec.code] = rec;
  if (typeof window !== 'undefined' && typeof sessionStorage !== 'undefined') {
    try {
      const map = getMockFamilies();
      map[rec.code] = rec;
      sessionStorage.setItem('udaan_mock_families', JSON.stringify(map));
    } catch {
      // Ignore storage errors
    }
  }
};

const getMockProgress = (code: string): AssessmentProgressResponse => {
  if (typeof window !== 'undefined' && typeof sessionStorage !== 'undefined') {
    try {
      const raw = sessionStorage.getItem(`udaan_mock_progress_${code}`);
      if (raw) return JSON.parse(raw);
    } catch {
      // fallback
    }
  }
  return inMemoryMockProgress[code] || { answers: {}, submitted: false };
};

const saveMockProgress = (code: string, prog: AssessmentProgressResponse) => {
  inMemoryMockProgress[code] = prog;
  if (typeof window !== 'undefined' && typeof sessionStorage !== 'undefined') {
    try {
      sessionStorage.setItem(`udaan_mock_progress_${code}`, JSON.stringify(prog));
    } catch {
      // fallback
    }
  }
};

const inMemoryMockIntakeProgress: Record<string, AssessmentProgressResponse> = {};

const getMockIntakeProgress = (code: string): AssessmentProgressResponse => {
  if (typeof window !== 'undefined' && typeof sessionStorage !== 'undefined') {
    try {
      const raw = sessionStorage.getItem(`udaan_mock_intake_progress_${code}`);
      if (raw) return JSON.parse(raw);
    } catch {
      // fallback
    }
  }
  return inMemoryMockIntakeProgress[code] || { answers: {}, submitted: false };
};

const saveMockIntakeProgress = (code: string, prog: AssessmentProgressResponse) => {
  inMemoryMockIntakeProgress[code] = prog;
  if (typeof window !== 'undefined' && typeof sessionStorage !== 'undefined') {
    try {
      sessionStorage.setItem(`udaan_mock_intake_progress_${code}`, JSON.stringify(prog));
    } catch {
      // fallback
    }
  }
};

// Generic fetch wrapper with contract error parsing
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${getApiBaseUrl()}${endpoint}`;
  let response: Response;

  try {
    response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...options.headers,
      },
    });
  } catch (err) {
    throw new ApiError(
      'network_error',
      err instanceof Error ? err.message : 'Network connection failed',
      0
    );
  }

  if (!response.ok) {
    let errorCode = 'unknown_error';
    let errorMessage = response.statusText;
    let missing: string[] | undefined;

    try {
      const data = (await response.json()) as ApiErrorShape;
      if (data && data.error) {
        errorCode = data.error.code || errorCode;
        errorMessage = data.error.message || errorMessage;
        missing = data.error.missing;
      }
    } catch {
      // Body was not JSON
    }

    throw new ApiError(errorCode, errorMessage, response.status, missing);
  }

  return (await response.json()) as T;
}

// ==========================================
// Family API Functions
// ==========================================
export async function createFamily(data: CreateFamilyPayload): Promise<CreateFamilyResponse> {
  if (isMockEnabled()) {
    const chars = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';
    let code = '';
    for (let i = 0; i < 6; i++) {
      code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    const record: MockFamilyRecord = {
      code,
      creatorRole: data.role,
      creatorName: data.name,
      creatorLang: data.lang,
      createdAt: Date.now(),
    };
    saveMockFamily(record);

    return {
      family_code: code,
      member_token: `mock-creator-token-${code}`,
      role: data.role,
      expires_at: new Date(Date.now() + 120 * 60 * 1000).toISOString(),
    };
  }

  return request<CreateFamilyResponse>('/families', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function previewFamily(familyCode: string): Promise<PreviewFamilyResponse> {
  const cleanCode = familyCode.trim().toUpperCase().replace(/[\s-]/g, '');

  if (isMockEnabled()) {
    if (cleanCode === 'NOTFND') {
      throw new ApiError('family_not_found', 'Family not found', 404);
    }
    if (cleanCode === 'FULL99') {
      return {
        family_code: cleanCode,
        open_role: null,
        creator_name: 'Priya',
      };
    }
    const map = getMockFamilies();
    const existing = map[cleanCode];
    if (existing) {
      const openRole: Role | null =
        existing.joinedRole ? null : existing.creatorRole === 'student' ? 'parent' : 'student';
      return {
        family_code: cleanCode,
        open_role: openRole,
        creator_name: existing.creatorName,
      };
    }
    // Default mock preview
    return {
      family_code: cleanCode,
      open_role: 'parent',
      creator_name: 'Rahul',
    };
  }

  return request<PreviewFamilyResponse>(`/families/${encodeURIComponent(cleanCode)}/preview`, {
    method: 'GET',
  });
}

export async function joinFamily(
  familyCode: string,
  data: JoinFamilyPayload
): Promise<JoinFamilyResponse> {
  const cleanCode = familyCode.trim().toUpperCase().replace(/[\s-]/g, '');

  if (isMockEnabled()) {
    if (cleanCode === 'NOTFND') {
      throw new ApiError('family_not_found', 'Family not found', 404);
    }
    if (cleanCode === 'FULL99') {
      throw new ApiError('family_full', 'Family already full', 409);
    }
    if (cleanCode === 'TAKEN1' && data.role === 'student') {
      throw new ApiError('role_taken', 'Role already taken in this family', 409);
    }

    const map = getMockFamilies();
    const existing = map[cleanCode];
    const partnerRole: Role = data.role === 'student' ? 'parent' : 'student';
    const partnerName = existing ? existing.creatorName : 'Mock Partner';

    if (existing) {
      if (existing.creatorRole === data.role) {
        throw new ApiError('role_taken', 'Role already taken in this family', 409);
      }
      existing.joinedRole = data.role;
      existing.joinedName = data.name;
      saveMockFamily(existing);
    }

    return {
      family_code: cleanCode,
      member_token: `mock-joined-token-${cleanCode}`,
      role: data.role,
      partner: {
        role: partnerRole,
        name: partnerName,
      },
      expires_at: new Date(Date.now() + 120 * 60 * 1000).toISOString(),
    };
  }

  return request<JoinFamilyResponse>(`/families/${encodeURIComponent(cleanCode)}/join`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getStatus(
  familyCode: string,
  memberToken: string
): Promise<FamilyStatusResponse> {
  const cleanCode = familyCode.trim().toUpperCase().replace(/[\s-]/g, '');

  if (isMockEnabled()) {
    const map = getMockFamilies();
    const existing = map[cleanCode];

    const isCreator = memberToken.startsWith('mock-creator-token');
    const myRole: Role = existing
      ? isCreator
        ? existing.creatorRole
        : existing.joinedRole || (existing.creatorRole === 'student' ? 'parent' : 'student')
      : 'student';
    const myName = existing
      ? isCreator
        ? existing.creatorName
        : existing.joinedName || 'You'
      : 'User';

    const partnerRole: Role = myRole === 'student' ? 'parent' : 'student';
    const defaultPartnerName = partnerRole === 'parent' ? 'Sharma Ji' : 'Rohan';

    const elapsed = existing ? Date.now() - existing.createdAt : 7000;
    const isLinked = elapsed >= 6000 || !!existing?.joinedName;

    // In mock mode the partner becomes done about 6 seconds after submission
    if (
      existing?.parentSubmitted &&
      existing.parentSubmittedAt &&
      Date.now() - existing.parentSubmittedAt >= 6000 &&
      !existing.studentSubmitted
    ) {
      existing.studentSubmitted = true;
      saveMockFamily(existing);
    }

    if (
      existing?.studentSubmitted &&
      existing.studentSubmittedAt &&
      Date.now() - existing.studentSubmittedAt >= 6000 &&
      !existing.parentSubmitted
    ) {
      existing.parentSubmitted = true;
      saveMockFamily(existing);
    }

    const mySubmitted = myRole === 'student' ? existing?.studentSubmitted : existing?.parentSubmitted;
    const partnerSubmitted = partnerRole === 'student' ? existing?.studentSubmitted : existing?.parentSubmitted;

    return {
      family_code: cleanCode,
      linked: isLinked,
      you: {
        role: myRole,
        name: myName,
        done: !!mySubmitted,
      },
      partner: isLinked
        ? {
            role: partnerRole,
            name: existing?.joinedName || defaultPartnerName,
            done: !!partnerSubmitted,
          }
        : null,
      expires_at: new Date(Date.now() + 120 * 60 * 1000).toISOString(),
    };
  }

  return request<FamilyStatusResponse>(`/families/${encodeURIComponent(cleanCode)}/status`, {
    method: 'GET',
    headers: {
      'X-Member-Token': memberToken,
    },
  });
}

// ==========================================
// Canonical Career Domains (from engine/domains.py)
// ==========================================
export const CANONICAL_CAREER_DOMAIN_OPTIONS: QuestionOption[] = [
  {
    id: 'tech_engineering',
    label: { en: 'Technology & Engineering', hi: 'तकनीक और इंजीनियरिंग' },
  },
  {
    id: 'business_management',
    label: { en: 'Business & Management', hi: 'बिजनेस और मैनेजमेंट' },
  },
  {
    id: 'healthcare_medicine',
    label: { en: 'Healthcare & Medicine', hi: 'डॉक्टरी और स्वास्थ्य' },
  },
  {
    id: 'design_creative',
    label: { en: 'Design & Creative Arts', hi: 'डिजाइन और कला' },
  },
  {
    id: 'media_entertainment',
    label: { en: 'Media & Content Creation', hi: 'मीडिया और कंटेंट क्रिएशन' },
  },
  {
    id: 'humanities_law',
    label: { en: 'Humanities, Law & Social Sciences', hi: 'कला, कानून और समाज शास्त्र' },
  },
  {
    id: 'sciences',
    label: { en: 'Sciences & Research', hi: 'साइंस और रिसर्च' },
  },
];

const RELOCATION_OPTIONS: QuestionOption[] = [
  { id: 'home_city', label: { en: 'Within our home city / town', hi: 'अपने शहर / कस्बे में' } },
  { id: 'same_state', label: { en: 'Within our state', hi: 'अपने राज्य में' } },
  { id: 'anywhere_india', label: { en: 'Anywhere in India', hi: 'भारत में कहीं भी' } },
  { id: 'abroad_ok', label: { en: 'Abroad / International is fine too', hi: 'विदेश जाने में भी कोई आपत्ति नहीं' } },
];

const TIME_TO_EARN_OPTIONS: QuestionOption[] = [
  {
    id: 'within_4y',
    label: {
      en: 'Within 3 to 4 years (e.g., direct degree or diploma)',
      hi: '3 से 4 साल के भीतर (जैसे डिग्री या डिप्लोमा के तुरंत बाद)',
    },
  },
  {
    id: 'five_six',
    label: {
      en: 'In 5 to 6 years (e.g., professional degree like B.Tech / MBBS / Masters)',
      hi: '5 से 6 साल में (जैसे बी.टेक, एमबीबीएस या मास्टर्स के बाद)',
    },
  },
  {
    id: 'seven_plus',
    label: {
      en: '7+ years is fine (e.g., advanced research or specialization)',
      hi: '7 साल या उससे अधिक भी चलेगा (जैसे उच्च शोध या विशेषज्ञता)',
    },
  },
];

// ==========================================
// Mock Assessment Questions Bank (starter-2: 6 sections, 32 questions)
// Order: background, interests, aptitude, values, preferences, free_text
// ==========================================
export const MOCK_ASSESSMENT_SECTIONS: AssessmentSection[] = [
  {
    id: 'background',
    title: { en: 'Background', hi: 'पृष्ठभूमि' },
    description: { en: 'Academic stream and context', hi: 'आपकी पढ़ाई और पृष्ठभूमि' },
    questions: [
      {
        id: 'bg_stream',
        section_id: 'background',
        type: 'single_choice',
        prompt: {
          en: 'Which academic stream are you studying or planning to choose?',
          hi: 'आप कौन सी पढ़ाई (स्ट्रीम) कर रहे हैं या चुनने की सोच रहे हैं?',
        },
        required: true,
        options: [
          { id: 'science_maths', label: { en: 'Science (with Maths / PCM)', hi: 'साइंस (गणित के साथ / PCM)' } },
          { id: 'science_bio', label: { en: 'Science (with Biology / PCB)', hi: 'साइंस (बायोलॉजी के साथ / PCB)' } },
          { id: 'commerce', label: { en: 'Commerce', hi: 'कॉमर्स' } },
          { id: 'arts', label: { en: 'Arts / Humanities', hi: 'आर्ट्स / मानविकी' } },
          { id: 'vocational', label: { en: 'Vocational / Applied Skills', hi: 'व्यावसायिक / कौशल आधारित' } },
          { id: 'undecided', label: { en: 'Undecided / Not sure yet', hi: 'अभी तय नहीं किया' } },
        ],
      },
      {
        id: 'bg_marks_band',
        section_id: 'background',
        type: 'single_choice',
        prompt: {
          en: 'What is your typical score range in recent exams?',
          hi: 'हाल की परीक्षाओं में आपके आम तौर पर कितने अंक आते हैं?',
        },
        required: true,
        options: [
          { id: 'below_50', label: { en: 'Below 50%', hi: '50% से कम' } },
          { id: '50_60', label: { en: '50% to 60%', hi: '50% से 60%' } },
          { id: '60_75', label: { en: '60% to 75%', hi: '60% से 75%' } },
          { id: '75_90', label: { en: '75% to 90%', hi: '75% से 90%' } },
          { id: 'above_90', label: { en: 'Above 90%', hi: '90% से ऊपर' } },
          { id: 'not_yet', label: { en: 'Results not out yet', hi: 'नतीजे अभी नहीं आए हैं' } },
        ],
      },
      {
        id: 'bg_district',
        section_id: 'background',
        type: 'text',
        prompt: {
          en: 'Which district and state do you live in?',
          hi: 'आप किस जिले और राज्य में रहते हैं?',
        },
        required: true,
        placeholder: { en: 'e.g., Jaipur, Rajasthan', hi: 'जैसे, जयपुर, राजस्थान' },
      },
      {
        id: 'bg_languages',
        section_id: 'background',
        type: 'multi_choice',
        prompt: {
          en: 'Which languages are you comfortable speaking or writing in?',
          hi: 'आप किन भाषाओं में बात करने या लिखने में सहज हैं?',
        },
        required: true,
        options: [
          { id: 'english', label: { en: 'English', hi: 'अंग्रेज़ी' } },
          { id: 'hindi', label: { en: 'Hindi', hi: 'हिंदी' } },
          { id: 'tamil', label: { en: 'Tamil', hi: 'तमिल' } },
          { id: 'telugu', label: { en: 'Telugu', hi: 'तेलुगु' } },
          { id: 'kannada', label: { en: 'Kannada', hi: 'कन्नड़' } },
          { id: 'malayalam', label: { en: 'Malayalam', hi: 'मलयालम' } },
          { id: 'other', label: { en: 'Other', hi: 'अन्य' } },
        ],
      },
    ],
  },
  {
    id: 'interests',
    title: { en: 'Interests', hi: 'रुचियां' },
    description: { en: 'What activities naturally excite you', hi: 'जो काम आपको स्वाभाविक रूप से पसंद हैं' },
    questions: [
      {
        id: 'int_01',
        section_id: 'interests',
        type: 'scale',
        prompt: {
          en: 'How much would you enjoy fixing broken devices or building things with tools?',
          hi: 'टूटे उपकरणों को सुधारना या औजारों से नई चीजें बनाना आपको कितना पसंद आएगा?',
        },
        required: true,
        min: 1,
        max: 5,
        min_label: { en: 'Would not enjoy it', hi: 'बिल्कुल पसंद नहीं आएगा' },
        max_label: { en: 'Would enjoy it a lot', hi: 'बहुत पसंद आएगा' },
      },
      {
        id: 'int_02',
        section_id: 'interests',
        type: 'scale',
        prompt: {
          en: 'How much would you enjoy researching why things happen in science or nature?',
          hi: 'विज्ञान या प्रकृति में कोई चीज़ क्यों होती है, यह खोजना आपको कितना पसंद आएगा?',
        },
        required: true,
        min: 1,
        max: 5,
        min_label: { en: 'Would not enjoy it', hi: 'बिल्कुल पसंद नहीं आएगा' },
        max_label: { en: 'Would enjoy it a lot', hi: 'बहुत पसंद आएगा' },
      },
      {
        id: 'int_03',
        section_id: 'interests',
        type: 'scale',
        prompt: {
          en: 'How much would you enjoy writing creative stories or sketching illustrations?',
          hi: 'कहानियां लिखना या चित्र बनाना आपको कितना पसंद आएगा?',
        },
        required: true,
        min: 1,
        max: 5,
        min_label: { en: 'Would not enjoy it', hi: 'बिल्कुल पसंद नहीं आएगा' },
        max_label: { en: 'Would enjoy it a lot', hi: 'बहुत पसंद आएगा' },
      },
      {
        id: 'int_04',
        section_id: 'interests',
        type: 'scale',
        prompt: {
          en: 'How much would you enjoy teaching a school subject to a younger student?',
          hi: 'किसी छोटे बच्चे को कोई विषय पढ़ाना या समझाना आपको कितना पसंद आएगा?',
        },
        required: true,
        min: 1,
        max: 5,
        min_label: { en: 'Would not enjoy it', hi: 'बिल्कुल पसंद नहीं आएगा' },
        max_label: { en: 'Would enjoy it a lot', hi: 'बहुत पसंद आएगा' },
      },
      {
        id: 'int_05',
        section_id: 'interests',
        type: 'scale',
        prompt: {
          en: 'How much would you enjoy leading a group project and presenting the final plan?',
          hi: 'किसी ग्रुप प्रोजेक्ट का नेतृत्व करना और योजना पेश करना आपको कितना पसंद आएगा?',
        },
        required: true,
        min: 1,
        max: 5,
        min_label: { en: 'Would not enjoy it', hi: 'बिल्कुल पसंद नहीं आएगा' },
        max_label: { en: 'Would enjoy it a lot', hi: 'बहुत पसंद आएगा' },
      },
      {
        id: 'int_06',
        section_id: 'interests',
        type: 'scale',
        prompt: {
          en: 'How much would you enjoy keeping expense records and monthly budgets neat and organized?',
          hi: 'खर्चों का हिसाब और रिकॉर्ड व्यवस्थित रखना आपको कितना पसंद आएगा?',
        },
        required: true,
        min: 1,
        max: 5,
        min_label: { en: 'Would not enjoy it', hi: 'बिल्कुल पसंद नहीं आएगा' },
        max_label: { en: 'Would enjoy it a lot', hi: 'बहुत पसंद आएगा' },
      },
      {
        id: 'int_07',
        section_id: 'interests',
        type: 'scale',
        prompt: {
          en: 'How much would you enjoy assembling mechanical machinery or working out in the field?',
          hi: 'मशीनों के पुर्जे जोड़ना या खुले मैदान में काम करना आपको कितना पसंद आएगा?',
        },
        required: true,
        min: 1,
        max: 5,
        min_label: { en: 'Would not enjoy it', hi: 'बिल्कुल पसंद नहीं आएगा' },
        max_label: { en: 'Would enjoy it a lot', hi: 'बहुत पसंद आएगा' },
      },
      {
        id: 'int_08',
        section_id: 'interests',
        type: 'scale',
        prompt: {
          en: 'How much would you enjoy setting up experiments to test your own theories?',
          hi: 'अपनी परिकल्पनाओं को परखने के लिए छोटे प्रयोग करना आपको कितना पसंद आएगा?',
        },
        required: true,
        min: 1,
        max: 5,
        min_label: { en: 'Would not enjoy it', hi: 'बिल्कुल पसंद नहीं आएगा' },
        max_label: { en: 'Would enjoy it a lot', hi: 'बहुत पसंद आएगा' },
      },
      {
        id: 'int_09',
        section_id: 'interests',
        type: 'scale',
        prompt: {
          en: 'How much would you enjoy designing layouts, graphics, or poster visuals?',
          hi: 'पोस्टर, डिज़ाइन या विजुअल्स को सुंदर और आकर्षक बनाना आपको कितना पसंद आएगा?',
        },
        required: true,
        min: 1,
        max: 5,
        min_label: { en: 'Would not enjoy it', hi: 'बिल्कुल पसंद नहीं आएगा' },
        max_label: { en: 'Would enjoy it a lot', hi: 'बहुत पसंद आएगा' },
      },
      {
        id: 'int_10',
        section_id: 'interests',
        type: 'scale',
        prompt: {
          en: 'How much would you enjoy listening to a friend and helping them solve a difficult problem?',
          hi: 'किसी दोस्त की बात सुनकर उसकी परेशानी सुलझाने में मदद करना आपको कितना पसंद आएगा?',
        },
        required: true,
        min: 1,
        max: 5,
        min_label: { en: 'Would not enjoy it', hi: 'बिल्कुल पसंद नहीं आएगा' },
        max_label: { en: 'Would enjoy it a lot', hi: 'बहुत पसंद आएगा' },
      },
      {
        id: 'int_11',
        section_id: 'interests',
        type: 'scale',
        prompt: {
          en: 'How much would you enjoy pitching a new product idea and launching a small venture?',
          hi: 'किसी नए विचार को लोगों के सामने रखना और छोटा काम शुरू करना आपको कितना पसंद आएगा?',
        },
        required: true,
        min: 1,
        max: 5,
        min_label: { en: 'Would not enjoy it', hi: 'बिल्कुल पसंद नहीं आएगा' },
        max_label: { en: 'Would enjoy it a lot', hi: 'बहुत पसंद आएगा' },
      },
      {
        id: 'int_12',
        section_id: 'interests',
        type: 'scale',
        prompt: {
          en: 'How much would you enjoy organizing lists and data neatly in a spreadsheet?',
          hi: 'स्प्रेडशीट में जानकारी और डेटा को करीने से व्यवस्थित करना आपको कितना पसंद आएगा?',
        },
        required: true,
        min: 1,
        max: 5,
        min_label: { en: 'Would not enjoy it', hi: 'बिल्कुल पसंद नहीं आएगा' },
        max_label: { en: 'Would enjoy it a lot', hi: 'बहुत पसंद आएगा' },
      },
    ],
  },
  {
    id: 'aptitude',
    title: { en: 'Aptitude', hi: 'योग्यता' },
    description: { en: 'Problem-solving and reasoning puzzles', hi: 'तार्किक व विश्लेषणात्मक पहेलियाँ' },
    questions: [
      {
        id: 'apt_spatial',
        section_id: 'aptitude',
        type: 'single_choice',
        prompt: {
          en: 'A solid cube is painted on all six outside faces and then sliced into 27 identical smaller cubes (3×3×3). How many of the smaller cubes have paint on exactly one face?',
          hi: 'एक ठोस घन के सभी छह बाहरी फलकों पर रंग किया जाता है और फिर उसे 27 एकसमान छोटे घनों (3×3×3) में काटा जाता है। इनमें से कितने छोटे घनों के केवल एक फलक पर रंग होगा?',
        },
        required: true,
        options: [
          { id: 'a', label: { en: '6', hi: '6' } },
          { id: 'b', label: { en: '8', hi: '8' } },
          { id: 'c', label: { en: '10', hi: '10' } },
          { id: 'd', label: { en: '12', hi: '12' } },
        ],
      },
      {
        id: 'apt_numerical',
        section_id: 'aptitude',
        type: 'single_choice',
        prompt: {
          en: 'A merchant marks an article at ₹1,200 and offers a 25% discount. If the merchant still earns a 20% profit on the cost price, what is the cost price?',
          hi: 'एक व्यापारी किसी वस्तु पर ₹1,200 अंकित करता है और 25% की छूट देता है। यदि वह फिर भी लागत मूल्य पर 20% लाभ कमाता है, तो वस्तु का लागत मूल्य क्या है?',
        },
        required: true,
        options: [
          { id: 'a', label: { en: '₹720', hi: '₹720' } },
          { id: 'b', label: { en: '₹750', hi: '₹750' } },
          { id: 'c', label: { en: '₹800', hi: '₹800' } },
          { id: 'd', label: { en: '₹840', hi: '₹840' } },
        ],
      },
      {
        id: 'apt_verbal',
        section_id: 'aptitude',
        type: 'single_choice',
        prompt: {
          en: "Consider the statement: 'All registered schools maintain a library. Some schools with libraries also have a computer lab.' Which conclusion must be true?",
          hi: "इस कथन पर विचार करें: 'सभी पंजीकृत स्कूलों में लाइब्रेरी होती है। लाइब्रेरी वाले कुछ स्कूलों में कंप्यूटर लैब भी है।' कौन सा निष्कर्ष निश्चित रूप से सत्य है?",
        },
        required: true,
        options: [
          { id: 'a', label: { en: 'All schools with computer labs are registered.', hi: 'कंप्यूटर लैब वाले सभी स्कूल पंजीकृत हैं।' } },
          { id: 'b', label: { en: 'Every registered school has a computer lab.', hi: 'प्रत्येक पंजीकृत स्कूल में कंप्यूटर लैब है।' } },
          { id: 'c', label: { en: 'At least some schools with computer labs have a library.', hi: 'कंप्यूटर लैब वाले कम से कम कुछ स्कूलों में लाइब्रेरी है।' } },
          { id: 'd', label: { en: 'No registered school lacks a computer lab.', hi: 'किसी भी पंजीकृत स्कूल में कंप्यूटर लैब की कमी नहीं है।' } },
        ],
      },
      {
        id: 'apt_logical',
        section_id: 'aptitude',
        type: 'single_choice',
        prompt: {
          en: 'In a 100m race with five runners: Bina finished ahead of Kamal. Chetan finished between Bina and Kamal. Kamal finished ahead of Deepa, and Arun finished behind Deepa. Who finished in last place?',
          hi: 'पाँच धावकों की दौड़ में: बीना कमल से आगे रही। चेतन बीना और कमल के बीच में रहा। कमल दीपा से आगे रहा, और अरुण दीपा से पीछे रहा। दौड़ में सबसे आखिरी स्थान पर कौन रहा?',
        },
        required: true,
        options: [
          { id: 'a', label: { en: 'Deepa', hi: 'दीपा' } },
          { id: 'b', label: { en: 'Kamal', hi: 'कमल' } },
          { id: 'c', label: { en: 'Chetan', hi: 'चेतन' } },
          { id: 'd', label: { en: 'Arun', hi: 'अरुण' } },
        ],
      },
    ],
  },
  {
    id: 'values',
    title: { en: 'Values', hi: 'कार्य मूल्य' },
    description: { en: 'What matters most in your future work', hi: 'करियर में आपके लिए सबसे अहम क्या है' },
    questions: [
      {
        id: 'val_security',
        section_id: 'values',
        type: 'slider',
        prompt: {
          en: 'How much does job security and steady income matter to you in a career?',
          hi: 'करियर में नौकरी की सुरक्षा और नियमित आय आपके लिए कितनी महत्वपूर्ण है?',
        },
        min: 0,
        max: 10,
        step: 1,
        min_label: { en: 'Not important', hi: 'महत्वपूर्ण नहीं' },
        max_label: { en: 'Extremely important', hi: 'बेहद महत्वपूर्ण' },
        required: true,
      },
      {
        id: 'val_independence',
        section_id: 'values',
        type: 'slider',
        prompt: {
          en: 'How much does having the freedom to work independently matter to you in a career?',
          hi: 'करियर में अपनी मर्जी और स्वतंत्रता से काम करना आपके लिए कितना महत्वपूर्ण है?',
        },
        min: 0,
        max: 10,
        step: 1,
        min_label: { en: 'Not important', hi: 'महत्वपूर्ण नहीं' },
        max_label: { en: 'Extremely important', hi: 'बेहद महत्वपूर्ण' },
        required: true,
      },
      {
        id: 'val_helping',
        section_id: 'values',
        type: 'slider',
        prompt: {
          en: 'How much does making a positive difference to society matter to you in a career?',
          hi: 'करियर में समाज और लोगों की भलाई के लिए काम करना आपके लिए कितना महत्वपूर्ण है?',
        },
        min: 0,
        max: 10,
        step: 1,
        min_label: { en: 'Not important', hi: 'महत्वपूर्ण नहीं' },
        max_label: { en: 'Extremely important', hi: 'बेहद महत्वपूर्ण' },
        required: true,
      },
      {
        id: 'val_income',
        section_id: 'values',
        type: 'slider',
        prompt: {
          en: 'How much does high earning potential and financial growth matter to you in a career?',
          hi: 'करियर में अधिक कमाई और आर्थिक तरक्की आपके लिए कितनी महत्वपूर्ण है?',
        },
        min: 0,
        max: 10,
        step: 1,
        min_label: { en: 'Not important', hi: 'महत्वपूर्ण नहीं' },
        max_label: { en: 'Extremely important', hi: 'बेहद महत्वपूर्ण' },
        required: true,
      },
      {
        id: 'val_creativity',
        section_id: 'values',
        type: 'slider',
        prompt: {
          en: 'How much does the chance to express new ideas and be creative matter to you in a career?',
          hi: 'करियर में नए विचार आजमाने और रचनात्मक होने का अवसर आपके लिए कितना महत्वपूर्ण है?',
        },
        min: 0,
        max: 10,
        step: 1,
        min_label: { en: 'Not important', hi: 'महत्वपूर्ण नहीं' },
        max_label: { en: 'Extremely important', hi: 'बेहद महत्वपूर्ण' },
        required: true,
      },
    ],
  },
  {
    id: 'preferences',
    title: { en: 'Preferences', hi: 'प्राथमिकताएँ' },
    description: { en: 'Work conditions, timelines, and career domains', hi: 'काम का माहौल, समय और करियर क्षेत्र' },
    questions: [
      {
        id: 'pref_risk_1',
        section_id: 'preferences',
        type: 'single_choice',
        prompt: {
          en: 'Imagine two starting job offers after college. Which would you choose?',
          hi: 'मान लें कि कॉलेज के बाद आपके सामने नौकरी के दो विकल्प हैं। आप किसे चुनेंगे?',
        },
        required: true,
        options: [
          {
            id: 'safe',
            label: {
              en: '₹3.5 lakh a year, guaranteed (illustrative)',
              hi: '₹3.5 लाख प्रति वर्ष, तय और सुरक्षित (अनुमानित)',
            },
          },
          {
            id: 'gamble',
            label: {
              en: '50% chance of ₹10 lakh a year, 50% chance of ₹2 lakh a year (illustrative)',
              hi: '50% संभावना ₹10 लाख प्रति वर्ष की, 50% संभावना ₹2 लाख प्रति वर्ष की (अनुमानित)',
            },
          },
        ],
      },
      {
        id: 'pref_risk_2',
        section_id: 'preferences',
        type: 'single_choice',
        prompt: {
          en: 'Imagine a different set of starting job offers. Which would you choose?',
          hi: 'अब मान लें कि आपके सामने ये दो विकल्प हैं। आप किसे चुनेंगे?',
        },
        required: true,
        options: [
          {
            id: 'safe',
            label: {
              en: '₹4.5 lakh a year, guaranteed (illustrative)',
              hi: '₹4.5 लाख प्रति वर्ष, तय और सुरक्षित (अनुमानित)',
            },
          },
          {
            id: 'gamble',
            label: {
              en: '50% chance of ₹10 lakh a year, 50% chance of ₹2 lakh a year (illustrative)',
              hi: '50% संभावना ₹10 लाख प्रति वर्ष की, 50% संभावना ₹2 लाख प्रति वर्ष की (अनुमानित)',
            },
          },
        ],
      },
      {
        id: 'pref_risk_3',
        section_id: 'preferences',
        type: 'single_choice',
        prompt: {
          en: 'Imagine a higher guaranteed offer vs the same variable opportunity. Which would you choose?',
          hi: 'मान लें कि एक अधिक सुरक्षित विकल्प और वही अनिश्चित अवसर सामने है। आप क्या चुनेंगे?',
        },
        required: true,
        options: [
          {
            id: 'safe',
            label: {
              en: '₹5.5 lakh a year, guaranteed (illustrative)',
              hi: '₹5.5 लाख प्रति वर्ष, तय और सुरक्षित (अनुमानित)',
            },
          },
          {
            id: 'gamble',
            label: {
              en: '50% chance of ₹10 lakh a year, 50% chance of ₹2 lakh a year (illustrative)',
              hi: '50% संभावना ₹10 लाख प्रति वर्ष की, 50% संभावना ₹2 लाख प्रति वर्ष की (अनुमानित)',
            },
          },
        ],
      },
      {
        id: 'pref_relocation',
        section_id: 'preferences',
        type: 'single_choice',
        prompt: {
          en: 'How far are you comfortable moving for higher studies or work?',
          hi: 'पढ़ाई या नौकरी के लिए आप कितनी दूर जाने में सहज हैं?',
        },
        required: true,
        options: RELOCATION_OPTIONS,
      },
      {
        id: 'pref_time_to_earn',
        section_id: 'preferences',
        type: 'single_choice',
        prompt: {
          en: 'How soon do you expect to start earning after completing school?',
          hi: 'स्कूल पूरा करने के बाद आप कब तक कमाई शुरू करने की उम्मीद करते हैं?',
        },
        required: true,
        options: TIME_TO_EARN_OPTIONS,
      },
      {
        id: 'pref_domain_wish',
        section_id: 'preferences',
        type: 'multi_choice',
        max_select: 3,
        prompt: {
          en: 'Which career domains are you most interested in exploring? (Select up to 3)',
          hi: 'आप किन क्षेत्रों में करियर बनाने के लिए सबसे अधिक उत्सुक हैं? (अधिकतम 3 चुनें)',
        },
        required: true,
        options: CANONICAL_CAREER_DOMAIN_OPTIONS,
      },
    ],
  },
  {
    id: 'free_text',
    title: { en: 'Free Text', hi: 'आपकी राय' },
    description: { en: 'Your passions in your own words', hi: 'अपने शब्दों में आपके शौक व विचार' },
    questions: [
      {
        id: 'free_text_1',
        section_id: 'free_text',
        type: 'long_text',
        prompt: {
          en: 'What do you do for fun? What problem around you would you like to fix?',
          hi: 'आप खाली समय में क्या करना पसंद करते हैं? अपने आस-पास की कौन सी समस्या को आप हल करना चाहेंगे?',
        },
        required: false,
        max_length: 600,
        placeholder: {
          en: 'Share your hobbies or issues you care about (optional)...',
          hi: 'अपने शौक या ऐसे मुद्दे साझा करें जिनकी आप परवाह करते हैं (वैकल्पिक)...',
        },
      },
    ],
  },
];

// ==========================================
// Assessment API Functions
// ==========================================
export async function getQuestions(
  familyCode: string,
  token: string
): Promise<AssessmentQuestionsResponse> {
  const cleanCode = familyCode.trim().toUpperCase().replace(/[\s-]/g, '');

  if (isMockEnabled()) {
    if (token.includes('parent-token-invalid')) {
      throw new ApiError('wrong_role', 'Parent cannot access student assessment', 403);
    }
    return { version: 'starter-2', sections: MOCK_ASSESSMENT_SECTIONS };
  }

  try {
    return await request<AssessmentQuestionsResponse>(
      `/families/${encodeURIComponent(cleanCode)}/assessment/questions`,
      {
        method: 'GET',
        headers: {
          'X-Member-Token': token,
        },
      }
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return { version: 'starter-2', sections: MOCK_ASSESSMENT_SECTIONS };
    }
    throw err;
  }
}

export async function getProgress(
  familyCode: string,
  token: string
): Promise<AssessmentProgressResponse> {
  const cleanCode = familyCode.trim().toUpperCase().replace(/[\s-]/g, '');

  if (isMockEnabled()) {
    if (token.includes('parent-token-invalid')) {
      throw new ApiError('wrong_role', 'Parent cannot access student assessment', 403);
    }
    return getMockProgress(cleanCode);
  }

  try {
    return await request<AssessmentProgressResponse>(
      `/families/${encodeURIComponent(cleanCode)}/assessment/progress`,
      {
        method: 'GET',
        headers: {
          'X-Member-Token': token,
        },
      }
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return getMockProgress(cleanCode);
    }
    throw err;
  }
}

export async function saveAnswers(
  familyCode: string,
  token: string,
  answers: Record<string, AnswerValue>
): Promise<SaveAnswersResponse> {
  const cleanCode = familyCode.trim().toUpperCase().replace(/[\s-]/g, '');

  if (isMockEnabled()) {
    if (token.includes('parent-token-invalid')) {
      throw new ApiError('wrong_role', 'Parent cannot access student assessment', 403);
    }
    const curr = getMockProgress(cleanCode);
    const updatedAnswers = { ...curr.answers, ...answers };
    const updated = { ...curr, answers: updatedAnswers };
    saveMockProgress(cleanCode, updated);

    return {
      saved: true,
      answers: updatedAnswers,
    };
  }

  try {
    return await request<SaveAnswersResponse>(
      `/families/${encodeURIComponent(cleanCode)}/assessment/answers`,
      {
        method: 'PUT',
        headers: {
          'X-Member-Token': token,
        },
        body: JSON.stringify({ answers }),
      }
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      const curr = getMockProgress(cleanCode);
      const updatedAnswers = { ...curr.answers, ...answers };
      const updated = { ...curr, answers: updatedAnswers };
      saveMockProgress(cleanCode, updated);

      return {
        saved: true,
        answers: updatedAnswers,
      };
    }
    throw err;
  }
}

export async function submitAssessment(
  familyCode: string,
  token: string
): Promise<SubmitAssessmentResponse> {
  const cleanCode = familyCode.trim().toUpperCase().replace(/[\s-]/g, '');

  if (isMockEnabled()) {
    if (token.includes('parent-token-invalid')) {
      throw new ApiError('wrong_role', 'Parent cannot access student assessment', 403);
    }

    const prog = getMockProgress(cleanCode);
    // Find missing required questions
    const allQuestions = MOCK_ASSESSMENT_SECTIONS.flatMap((s) => s.questions);
    const missing: string[] = [];

    for (const q of allQuestions) {
      if (q.required) {
        const val = prog.answers[q.id];
        if (
          val === undefined ||
          val === null ||
          val === '' ||
          (Array.isArray(val) && val.length === 0)
        ) {
          missing.push(q.id);
        }
      }
    }

    if (missing.length > 0) {
      throw new ApiError('assessment_incomplete', 'Assessment incomplete', 422, missing);
    }

    prog.submitted = true;
    saveMockProgress(cleanCode, prog);

    // Update family status record
    const fams = getMockFamilies();
    if (fams[cleanCode]) {
      fams[cleanCode].studentSubmitted = true;
      fams[cleanCode].studentSubmittedAt = Date.now();
      saveMockFamily(fams[cleanCode]);
    }

    return {
      submitted: true,
      done: true,
    };
  }

  try {
    return await request<SubmitAssessmentResponse>(
      `/families/${encodeURIComponent(cleanCode)}/assessment/submit`,
      {
        method: 'POST',
        headers: {
          'X-Member-Token': token,
        },
        body: JSON.stringify({}),
      }
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      const prog = getMockProgress(cleanCode);
      const allQuestions = MOCK_ASSESSMENT_SECTIONS.flatMap((s) => s.questions);
      const missing: string[] = [];

      for (const q of allQuestions) {
        if (q.required) {
          const val = prog.answers[q.id];
          if (
            val === undefined ||
            val === null ||
            val === '' ||
            (Array.isArray(val) && val.length === 0)
          ) {
            missing.push(q.id);
          }
        }
      }

      if (missing.length > 0) {
        throw new ApiError('assessment_incomplete', 'Assessment incomplete', 422, missing);
      }

      prog.submitted = true;
      saveMockProgress(cleanCode, prog);

      const fams = getMockFamilies();
      if (fams[cleanCode]) {
        fams[cleanCode].studentSubmitted = true;
        fams[cleanCode].studentSubmittedAt = Date.now();
        saveMockFamily(fams[cleanCode]);
      }

      return {
        submitted: true,
        done: true,
      };
    }
    throw err;
  }
}

// ==========================================
// Mock Parent Intake Bank (starter-2: 5 sections, 16 questions)
// Canonical domains from engine/domains.py
// ==========================================
export const MOCK_INTAKE_SECTIONS: AssessmentSection[] = [
  {
    id: 'money',
    title: { en: 'Education Budget', hi: 'शिक्षा बजट' },
    description: { en: 'Budget, savings, loan tolerance, and family cash flow', hi: 'बजट, बचत, ऋण क्षमता और मासिक संतुलन' },
    questions: [
      {
        id: 'income_band',
        section_id: 'money',
        type: 'single_choice',
        prompt: {
          en: 'What is your approximate annual family income?',
          hi: 'आपके परिवार की लगभग वार्षिक आय कितनी है?',
        },
        required: true,
        options: [
          { id: 'under_3l', label: { en: 'Under ₹3 lakh', hi: '₹3 लाख से कम' } },
          { id: '3_6l', label: { en: '₹3 lakh to ₹6 lakh', hi: '₹3 लाख से ₹6 लाख' } },
          { id: '6_12l', label: { en: '₹6 lakh to ₹12 lakh', hi: '₹6 लाख से ₹12 लाख' } },
          { id: '12_25l', label: { en: '₹12 lakh to ₹25 lakh', hi: '₹12 लाख से ₹25 लाख' } },
          { id: 'over_25l', label: { en: 'Over ₹25 lakh', hi: '₹25 लाख से अधिक' } },
        ],
      },
      {
        id: 'savings_band',
        section_id: 'money',
        type: 'single_choice',
        prompt: {
          en: "How much savings have you set aside for your child's higher education?",
          hi: 'आपने बच्चे की उच्च शिक्षा के लिए लगभग कितनी बचत रखी है?',
        },
        required: true,
        options: [
          { id: 'none', label: { en: 'No dedicated savings yet', hi: 'अभी कोई अलग बचत नहीं है' } },
          { id: 'under_1l', label: { en: 'Under ₹1 lakh', hi: '₹1 लाख से कम' } },
          { id: '1_3l', label: { en: '₹1 lakh to ₹3 lakh', hi: '₹1 लाख से ₹3 लाख' } },
          { id: '3_8l', label: { en: '₹3 lakh to ₹8 lakh', hi: '₹3 लाख से ₹8 लाख' } },
          { id: 'over_8l', label: { en: 'Over ₹8 lakh', hi: '₹8 लाख से अधिक' } },
        ],
      },
      {
        id: 'loan_band',
        section_id: 'money',
        type: 'single_choice',
        prompt: {
          en: 'What amount of education loan would your family feel comfortable taking?',
          hi: 'आपकी पारिवारिक स्थिति के अनुसार आप कितना शिक्षा ऋण (लोन) लेने में सहज हैं?',
        },
        required: true,
        options: [
          { id: 'none', label: { en: 'Prefer no loan at all', hi: 'लोन बिल्कुल नहीं लेना चाहते' } },
          { id: 'up_to_3l', label: { en: 'Up to ₹3 lakh', hi: '₹3 लाख तक' } },
          { id: '3_8l', label: { en: '₹3 lakh to ₹8 lakh', hi: '₹3 लाख से ₹8 लाख' } },
          { id: '8_15l', label: { en: '₹8 lakh to ₹15 lakh', hi: '₹8 लाख से ₹15 लाख' } },
          { id: 'over_15l', label: { en: 'Over ₹15 lakh', hi: '₹15 लाख से अधिक' } },
        ],
      },
      {
        id: 'surplus_band',
        section_id: 'money',
        type: 'single_choice',
        prompt: {
          en: 'How much money is left over each month after all expenses?',
          hi: 'हर महीने सारे खर्चों के बाद परिवार के पास लगभग कितनी बचत बचती है?',
        },
        required: true,
        options: [
          { id: 'none', label: { en: 'None', hi: 'कुछ नहीं' } },
          { id: 'under_5k', label: { en: 'Under ₹5,000 (illustrative)', hi: '₹5,000 से कम (अनुमानित)' } },
          { id: '5k_15k', label: { en: '₹5,000 to ₹15,000 (illustrative)', hi: '₹5,000 से ₹15,000 (अनुमानित)' } },
          { id: '15k_30k', label: { en: '₹15,000 to ₹30,000 (illustrative)', hi: '₹15,000 से ₹30,000 (अनुमानित)' } },
          { id: 'over_30k', label: { en: 'Over ₹30,000 (illustrative)', hi: '₹30,000 से अधिक (अनुमानित)' } },
        ],
      },
      {
        id: 'emi_band',
        section_id: 'money',
        type: 'single_choice',
        prompt: {
          en: 'What total loan EMIs does the family already pay each month?',
          hi: 'परिवार हर महीने कुल कितनी लोन ईएमआई (EMI) भरता है?',
        },
        required: true,
        options: [
          { id: 'none', label: { en: 'None', hi: 'कोई ईएमआई नहीं' } },
          { id: 'under_5k', label: { en: 'Under ₹5,000 (illustrative)', hi: '₹5,000 से कम (अनुमानित)' } },
          { id: '5k_15k', label: { en: '₹5,000 to ₹15,000 (illustrative)', hi: '₹5,000 से ₹15,000 (अनुमानित)' } },
          { id: 'over_15k', label: { en: 'Over ₹15,000 (illustrative)', hi: '₹15,000 से अधिक (अनुमानित)' } },
        ],
      },
    ],
  },
  {
    id: 'risk',
    title: { en: 'Career Risk & Return', hi: 'करियर जोखिम और लाभ' },
    description: { en: 'Risk preference on post-college job outcomes', hi: 'कॉलेज के बाद करियर सुरक्षा और जोखिम' },
    questions: [
      {
        id: 'risk_1',
        section_id: 'risk',
        type: 'single_choice',
        prompt: {
          en: 'Imagine two starting job offers for your child after college. Which would you prefer they choose?',
          hi: 'कल्पना करें कि कॉलेज के बाद आपके बच्चे के सामने नौकरी के दो विकल्प हैं। आप किसे प्राथमिकता देंगे?',
        },
        required: true,
        options: [
          {
            id: 'safe',
            label: {
              en: '₹3.5 lakh a year, guaranteed (illustrative)',
              hi: '₹3.5 लाख प्रति वर्ष, तय और सुरक्षित (अनुमानित)',
            },
          },
          {
            id: 'gamble',
            label: {
              en: '50% chance of ₹10 lakh a year, 50% chance of ₹2 lakh a year (illustrative)',
              hi: '50% संभावना ₹10 लाख प्रति वर्ष की, 50% संभावना ₹2 लाख प्रति वर्ष की (अनुमानित)',
            },
          },
        ],
      },
      {
        id: 'risk_2',
        section_id: 'risk',
        type: 'single_choice',
        prompt: {
          en: 'Imagine a different set of starting job offers for your child. Which would you prefer they choose?',
          hi: 'अब मान लें कि आपके बच्चे के सामने ये दो विकल्प हैं। आप किसे बेहतर मानेंगे?',
        },
        required: true,
        options: [
          {
            id: 'safe',
            label: {
              en: '₹4.5 lakh a year, guaranteed (illustrative)',
              hi: '₹4.5 लाख प्रति वर्ष, तय और सुरक्षित (अनुमानित)',
            },
          },
          {
            id: 'gamble',
            label: {
              en: '50% chance of ₹10 lakh a year, 50% chance of ₹2 lakh a year (illustrative)',
              hi: '50% संभावना ₹10 लाख प्रति वर्ष की, 50% संभावना ₹2 लाख प्रति वर्ष की (अनुमानित)',
            },
          },
        ],
      },
      {
        id: 'risk_3',
        section_id: 'risk',
        type: 'single_choice',
        prompt: {
          en: 'Imagine a higher guaranteed offer vs the same variable opportunity. Which would you prefer they choose?',
          hi: 'मान लें कि एक अधिक सुरक्षित विकल्प और वही अनिश्चित अवसर सामने है। आप क्या चुनेंगे?',
        },
        required: true,
        options: [
          {
            id: 'safe',
            label: {
              en: '₹5.5 lakh a year, guaranteed (illustrative)',
              hi: '₹5.5 लाख प्रति वर्ष, तय और सुरक्षित (अनुमानित)',
            },
          },
          {
            id: 'gamble',
            label: {
              en: '50% chance of ₹10 lakh a year, 50% chance of ₹2 lakh a year (illustrative)',
              hi: '50% संभावना ₹10 लाख प्रति वर्ष की, 50% संभावना ₹2 लाख प्रति वर्ष की (अनुमानित)',
            },
          },
        ],
      },
    ],
  },
  {
    id: 'plans',
    title: { en: 'Future Plans', hi: 'भविष्य की योजनाएं' },
    description: { en: 'Relocation boundaries and timeline expectations', hi: 'शहर से दूरी और कमाई शुरू करने का समय' },
    questions: [
      {
        id: 'relocation',
        section_id: 'plans',
        type: 'single_choice',
        prompt: {
          en: 'How far are you comfortable sending your child for higher studies or work?',
          hi: 'पढ़ाई या नौकरी के लिए आप अपने बच्चे को कितनी दूर भेजने में सहज हैं?',
        },
        required: true,
        options: RELOCATION_OPTIONS,
      },
      {
        id: 'time_to_earn',
        section_id: 'plans',
        type: 'single_choice',
        prompt: {
          en: 'How soon do you expect your child to start earning after completing school?',
          hi: 'स्कूल पूरा करने के बाद आप बच्चे से कब तक कमाई शुरू करने की उम्मीद करते हैं?',
        },
        required: true,
        options: TIME_TO_EARN_OPTIONS,
      },
    ],
  },
  {
    id: 'hopes',
    title: { en: 'Aspirations & Hopes', hi: 'उम्मीदें और प्राथमिकताएं' },
    description: { en: 'Aspirational career domains and non-negotiables', hi: 'पसंदीदा करियर क्षेत्र और मुख्य प्राथमिकताएँ' },
    questions: [
      {
        id: 'domain_wish',
        section_id: 'hopes',
        type: 'multi_choice',
        max_select: 3,
        prompt: {
          en: 'Which career domains do you hope your child considers? (Pick up to 3)',
          hi: 'आप किन क्षेत्रों में अपने बच्चे के जाने की उम्मीद रखते हैं? (अधिकतम 3 चुनें)',
        },
        required: true,
        options: CANONICAL_CAREER_DOMAIN_OPTIONS,
      },
      {
        id: 'non_negotiables',
        section_id: 'hopes',
        type: 'multi_choice',
        prompt: {
          en: 'Are there any factors you consider non-negotiable for their career?',
          hi: 'क्या ऐसी कोई बातें हैं जिन पर आप बिल्कुल समझौता नहीं करना चाहते?',
        },
        required: false,
        options: [
          { id: 'near_home', label: { en: 'Must stay close to family', hi: 'परिवार के पास रहना जरूरी' } },
          { id: 'job_security', label: { en: 'High job security is essential', hi: 'नौकरी की सुरक्षा सबसे जरूरी' } },
          { id: 'govt_or_public', label: { en: 'Government or public sector preferred', hi: 'सरकारी या सार्वजनिक क्षेत्र को प्राथमिकता' } },
          { id: 'low_loan', label: { en: 'Must avoid heavy education debt', hi: 'भारी कर्ज से बचना जरूरी' } },
        ],
      },
      {
        id: 'hope_text',
        section_id: 'hopes',
        type: 'long_text',
        prompt: {
          en: "In your own words, what is your biggest hope or dream for your child's future?",
          hi: 'अपने शब्दों में बताएं, अपने बच्चे के भविष्य के लिए आपकी सबसे बड़ी उम्मीद या सपना क्या है?',
        },
        required: false,
        max_length: 600,
        placeholder: {
          en: 'Share your thoughts, expectations, or concerns (optional)...',
          hi: 'अपने विचार, उम्मीदें या चिंताएं साझा करें (वैकल्पिक)...',
        },
      },
    ],
  },
  {
    id: 'perception',
    title: { en: 'Understanding Your Child', hi: 'बच्चे की पसंद की समझ' },
    description: { en: 'What you perceive about your child’s interests and risk appetite', hi: 'बच्चे की रुचियों और जोखिम लेने की समझ' },
    questions: [
      {
        id: 'guess_domain',
        section_id: 'perception',
        type: 'single_choice',
        prompt: {
          en: 'Which field do you think your child is most interested in?',
          hi: 'आपको क्या लगता है, आपका बच्चा किस क्षेत्र में सबसे ज्यादा रुचि रखता है?',
        },
        required: true,
        options: [
          ...CANONICAL_CAREER_DOMAIN_OPTIONS,
          { id: 'not_sure', label: { en: 'Not sure / Open to anything', hi: 'पक्का नहीं पता / किसी भी क्षेत्र में' } },
        ],
      },
      {
        id: 'guess_relocation',
        section_id: 'perception',
        type: 'single_choice',
        prompt: {
          en: 'How far do you think your child is willing to move for college or work?',
          hi: 'आपको क्या लगता है, आपका बच्चा कॉलेज या काम के लिए कितनी दूर जाने को तैयार है?',
        },
        required: true,
        options: RELOCATION_OPTIONS,
      },
      {
        id: 'guess_risk',
        section_id: 'perception',
        type: 'single_choice',
        prompt: {
          en: "How would you describe your child's appetite for career risk?",
          hi: 'करियर में जोखिम लेने के मामले में आपके बच्चे का रवैया कैसा है?',
        },
        required: true,
        options: [
          { id: 'low', label: { en: 'Prefers safe, predictable options', hi: 'सुरक्षित और तय रास्ते पसंद करता/करती है' } },
          { id: 'medium', label: { en: 'Balanced: open to reasonable risks', hi: 'संतुलित: सोच-समझकर जोखिम ले सकता/सकती है' } },
          { id: 'high', label: { en: 'Ambitious: willing to take big risks for big rewards', hi: 'महत्वाकांक्षी: बड़े अवसरों के लिए बड़ा जोखिम लेने को तैयार' } },
        ],
      },
    ],
  },
];

// ==========================================
// Parent Intake API Functions
// ==========================================
export async function getIntakeQuestions(
  familyCode: string,
  token: string
): Promise<AssessmentQuestionsResponse> {
  const cleanCode = familyCode.trim().toUpperCase().replace(/[\s-]/g, '');

  if (isMockEnabled()) {
    if (token.includes('student-token-invalid')) {
      throw new ApiError('wrong_role', 'Student cannot access parent intake', 403);
    }
    return { version: 'starter-2', sections: MOCK_INTAKE_SECTIONS };
  }

  try {
    return await request<AssessmentQuestionsResponse>(
      `/families/${encodeURIComponent(cleanCode)}/intake/questions`,
      {
        method: 'GET',
        headers: {
          'X-Member-Token': token,
        },
      }
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return { version: 'starter-2', sections: MOCK_INTAKE_SECTIONS };
    }
    throw err;
  }
}

export async function getIntakeProgress(
  familyCode: string,
  token: string
): Promise<AssessmentProgressResponse> {
  const cleanCode = familyCode.trim().toUpperCase().replace(/[\s-]/g, '');

  if (isMockEnabled()) {
    if (token.includes('student-token-invalid')) {
      throw new ApiError('wrong_role', 'Student cannot access parent intake', 403);
    }
    return getMockIntakeProgress(cleanCode);
  }

  try {
    return await request<AssessmentProgressResponse>(
      `/families/${encodeURIComponent(cleanCode)}/intake/progress`,
      {
        method: 'GET',
        headers: {
          'X-Member-Token': token,
        },
      }
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return getMockIntakeProgress(cleanCode);
    }
    throw err;
  }
}

export async function saveIntakeAnswers(
  familyCode: string,
  token: string,
  answers: Record<string, AnswerValue>
): Promise<SaveAnswersResponse> {
  const cleanCode = familyCode.trim().toUpperCase().replace(/[\s-]/g, '');

  if (isMockEnabled()) {
    if (token.includes('student-token-invalid')) {
      throw new ApiError('wrong_role', 'Student cannot access parent intake', 403);
    }
    const curr = getMockIntakeProgress(cleanCode);
    const updatedAnswers = { ...curr.answers, ...answers };
    const updated = { ...curr, answers: updatedAnswers };
    saveMockIntakeProgress(cleanCode, updated);

    return {
      saved: true,
      answers: updatedAnswers,
    };
  }

  try {
    return await request<SaveAnswersResponse>(
      `/families/${encodeURIComponent(cleanCode)}/intake/answers`,
      {
        method: 'PUT',
        headers: {
          'X-Member-Token': token,
        },
        body: JSON.stringify({ answers }),
      }
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      const curr = getMockIntakeProgress(cleanCode);
      const updatedAnswers = { ...curr.answers, ...answers };
      const updated = { ...curr, answers: updatedAnswers };
      saveMockIntakeProgress(cleanCode, updated);

      return {
        saved: true,
        answers: updatedAnswers,
      };
    }
    throw err;
  }
}

export async function submitIntake(
  familyCode: string,
  token: string
): Promise<SubmitAssessmentResponse> {
  const cleanCode = familyCode.trim().toUpperCase().replace(/[\s-]/g, '');

  if (isMockEnabled()) {
    if (token.includes('student-token-invalid')) {
      throw new ApiError('wrong_role', 'Student cannot access parent intake', 403);
    }

    const prog = getMockIntakeProgress(cleanCode);
    const allQuestions = MOCK_INTAKE_SECTIONS.flatMap((s) => s.questions);
    const missing: string[] = [];

    for (const q of allQuestions) {
      if (q.required) {
        const val = prog.answers[q.id];
        if (
          val === undefined ||
          val === null ||
          val === '' ||
          (Array.isArray(val) && val.length === 0)
        ) {
          missing.push(q.id);
        }
      }
    }

    if (missing.length > 0) {
      throw new ApiError('intake_incomplete', 'Intake incomplete', 422, missing);
    }

    prog.submitted = true;
    saveMockIntakeProgress(cleanCode, prog);

    const fams = getMockFamilies();
    if (fams[cleanCode]) {
      fams[cleanCode].parentSubmitted = true;
      fams[cleanCode].parentSubmittedAt = Date.now();
      saveMockFamily(fams[cleanCode]);
    }

    return {
      submitted: true,
      done: true,
    };
  }

  try {
    return await request<SubmitAssessmentResponse>(
      `/families/${encodeURIComponent(cleanCode)}/intake/submit`,
      {
        method: 'POST',
        headers: {
          'X-Member-Token': token,
        },
        body: JSON.stringify({}),
      }
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      const prog = getMockIntakeProgress(cleanCode);
      const allQuestions = MOCK_INTAKE_SECTIONS.flatMap((s) => s.questions);
      const missing: string[] = [];

      for (const q of allQuestions) {
        if (q.required) {
          const val = prog.answers[q.id];
          if (
            val === undefined ||
            val === null ||
            val === '' ||
            (Array.isArray(val) && val.length === 0)
          ) {
            missing.push(q.id);
          }
        }
      }

      if (missing.length > 0) {
        throw new ApiError('intake_incomplete', 'Intake incomplete', 422, missing);
      }

      prog.submitted = true;
      saveMockIntakeProgress(cleanCode, prog);

      const fams = getMockFamilies();
      if (fams[cleanCode]) {
        fams[cleanCode].parentSubmitted = true;
        fams[cleanCode].parentSubmittedAt = Date.now();
        saveMockFamily(fams[cleanCode]);
      }

      return {
        submitted: true,
        done: true,
      };
    }
    throw err;
  }
}

// ==========================================
// Mirror (Page 5) API Functions & Mock Data
// ==========================================

// Clearly marked mock response for Family Mirror per API contract
export const MOCK_MIRROR_RESPONSE: MirrorResponse = {
  conflict_index: 16.5,
  dimensions: [
    {
      id: 'risk',
      gap: 0.33,
      weight: 0.25,
      kind: 'scale',
      steps: [
        {
          id: 'risk_0',
          label: {
            en: 'Chose the guaranteed offer every time',
            hi: 'हर बार पक्की कमाई वाला विकल्प चुना',
          },
        },
        {
          id: 'risk_1',
          label: {
            en: 'Chose the gamble once',
            hi: 'एक बार जोखिम वाला विकल्प चुना',
          },
        },
        {
          id: 'risk_2',
          label: {
            en: 'Chose the gamble twice',
            hi: 'दो बार जोखिम वाला विकल्प चुना',
          },
        },
        {
          id: 'risk_3',
          label: {
            en: 'Chose the gamble every time',
            hi: 'हर बार जोखिम वाला विकल्प चुना',
          },
        },
      ],
      student_step: 1,
      parent_step: 0,
    },
    {
      id: 'domain',
      gap: 0.0,
      weight: 0.25,
      kind: 'picks',
      options: CANONICAL_CAREER_DOMAIN_OPTIONS,
      student_picks: ['tech_engineering'],
      parent_picks: ['tech_engineering'],
      parent_guess: 'tech_engineering',
    },
    {
      id: 'relocation',
      gap: 0.33,
      weight: 0.25,
      kind: 'scale',
      steps: [
        {
          id: 'home_city',
          label: {
            en: 'Within our home city / town',
            hi: 'अपने शहर / कस्बे में',
          },
        },
        {
          id: 'same_state',
          label: {
            en: 'Within our state',
            hi: 'अपने राज्य में',
          },
        },
        {
          id: 'anywhere_india',
          label: {
            en: 'Anywhere in India',
            hi: 'भारत में कहीं भी',
          },
        },
        {
          id: 'abroad_ok',
          label: {
            en: 'Abroad / International is fine too',
            hi: 'विदेश जाने में भी कोई आपत्ति नहीं',
          },
        },
      ],
      student_step: 0,
      parent_step: 1,
    },
    {
      id: 'time',
      gap: 0.0,
      weight: 0.25,
      kind: 'scale',
      steps: [
        {
          id: 'within_4y',
          label: {
            en: 'About 4 years (e.g., a regular degree, B.Tech or a diploma)',
            hi: 'लगभग 4 साल (जैसे सामान्य डिग्री, बी.टेक या डिप्लोमा)',
          },
        },
        {
          id: 'five_six',
          label: {
            en: 'About 5 to 6 years (e.g., MBBS, 5-year law, or a degree plus a Master\'s)',
            hi: 'लगभग 5 से 6 साल (जैसे एमबीबीएस, 5 साल का लॉ, या डिग्री के बाद मास्टर्स)',
          },
        },
        {
          id: 'seven_plus',
          label: {
            en: '7 years or more is fine (e.g., MD/MS or a PhD)',
            hi: '7 साल या उससे ज़्यादा भी चलेगा (जैसे एमडी/एमएस या पीएचडी)',
          },
        },
      ],
      student_step: 0,
      parent_step: 0,
    },
  ],
};

export async function getMirror(
  familyCode: string,
  token: string
): Promise<MirrorResponse> {
  const cleanCode = familyCode.trim().toUpperCase().replace(/[\s-]/g, '');

  if (isMockEnabled()) {
    if (cleanCode === 'NOTFND') {
      throw new ApiError('family_not_found', 'Family not found', 404);
    }
    const map = getMockFamilies();
    const existing = map[cleanCode];
    if (existing && (!existing.studentSubmitted || !existing.parentSubmitted)) {
      throw new ApiError('mirror_not_ready', 'Both members must submit before viewing mirror', 409);
    }
    return MOCK_MIRROR_RESPONSE;
  }

  try {
    return await request<MirrorResponse>(
      `/families/${encodeURIComponent(cleanCode)}/mirror`,
      {
        method: 'GET',
        headers: {
          'X-Member-Token': token,
        },
      }
    );
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return MOCK_MIRROR_RESPONSE;
    }
    throw err;
  }
}

