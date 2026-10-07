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
// Mock Assessment Questions Bank
// (5 sections, at least 2 of every question type)
// ==========================================
export const MOCK_ASSESSMENT_SECTIONS: AssessmentSection[] = [
  {
    id: 'sec_interests',
    title: { en: 'Interests', hi: 'रुचियाँ' },
    description: { en: 'What naturally excites you', hi: 'जो काम आपको स्वाभाविक रूप से पसंद हैं' },
    questions: [
      {
        id: 'q_int_activity',
        section_id: 'sec_interests',
        type: 'single_choice',
        prompt: {
          en: 'Which of these activities sounds most exciting to you on a weekend?',
          hi: 'वीकेंड पर इनमें से कौन-सा काम करना आपको सबसे रोमांचक लगेगा?',
        },
        required: true,
        options: [
          {
            id: 'opt_robot',
            label: {
              en: 'Building a working mechanical robot or physical gadget',
              hi: 'एक काम करने वाला रोबोट या गैजेट बनाना',
            },
          },
          {
            id: 'opt_story',
            label: {
              en: 'Writing an interactive story, script, or graphic novel',
              hi: 'एक कहानी, पटकथा या ग्राफ़िक नॉवेल लिखना',
            },
          },
          {
            id: 'opt_event',
            label: {
              en: 'Organizing a community campaign or volunteer event',
              hi: 'सामाजिक अभियान या स्वयंसेवा कार्यक्रम आयोजित करना',
            },
          },
          {
            id: 'opt_data',
            label: {
              en: 'Analyzing stocks, sports statistics, or scientific data',
              hi: 'खेल या विज्ञान के डेटा और आँकड़ों का विश्लेषण करना',
            },
          },
        ],
      },
      {
        id: 'q_int_fields',
        section_id: 'sec_interests',
        type: 'multi_choice',
        prompt: {
          en: 'Select up to 3 subjects or topics you genuinely enjoy exploring:',
          hi: 'अपनी पसंद के 3 विषय या क्षेत्र चुनें जिन्हें आप पढ़ना चाहते हैं:',
        },
        required: true,
        options: [
          { id: 'field_math', label: { en: 'Mathematics & Logic', hi: 'गणित और तर्कशास्त्र' } },
          { id: 'field_bio', label: { en: 'Biology & Healthcare', hi: 'जीव विज्ञान और चिकित्सा' } },
          { id: 'field_design', label: { en: 'Design & Visual Arts', hi: 'डिजाइन और दृश्य कला' } },
          { id: 'field_biz', label: { en: 'Economics & Business Strategy', hi: 'अर्थशास्त्र और व्यापार' } },
          { id: 'field_tech', label: { en: 'Technology & Programming', hi: 'तकनीक और प्रोग्रामिंग' } },
          { id: 'field_soc', label: { en: 'Law, Politics & Social Sciences', hi: 'कानून और राजनीति' } },
        ],
      },
    ],
  },
  {
    id: 'sec_strengths',
    title: { en: 'Strengths', hi: 'ताकत व कौशल' },
    description: { en: 'How you solve challenges', hi: 'चुनौतियों को सुलझाने की आपकी क्षमता' },
    questions: [
      {
        id: 'q_str_math',
        section_id: 'sec_strengths',
        type: 'scale',
        prompt: {
          en: 'How comfortable are you breaking down complex quantitative puzzles?',
          hi: 'जटिल गणितीय या तार्किक पहेलियों को सुलझाने में आप कितने सहज हैं?',
        },
        min: 1,
        max: 5,
        min_label: { en: 'Challenging for me', hi: 'कठिन लगता है' },
        max_label: { en: 'Very comfortable', hi: 'बहुत आसान लगता है' },
        required: true,
      },
      {
        id: 'q_str_proud',
        section_id: 'sec_strengths',
        type: 'text',
        prompt: {
          en: 'Name one achievement or project you are especially proud of:',
          hi: 'किसी ऐसी उपलब्धि या प्रोजेक्ट का नाम लिखें जिस पर आपको गर्व है:',
        },
        required: false,
        placeholder: { en: 'e.g. Science fair exhibition, debate trophy...', hi: 'उदा. विज्ञान मेला, वाद-विवाद प्रतियोगिता...' },
      },
    ],
  },
  {
    id: 'sec_work_style',
    title: { en: 'Work Style', hi: 'काम करने का तरीका' },
    description: { en: 'Your ideal day-to-day dynamic', hi: 'रोज़मर्रा के काम का आपका पसंदीदा माहौल' },
    questions: [
      {
        id: 'q_ws_environment',
        section_id: 'sec_work_style',
        type: 'single_choice',
        prompt: {
          en: 'Where do you do your best thinking and focused work?',
          hi: 'आप सबसे अच्छा ध्यान लगाकर कहाँ काम कर पाते हैं?',
        },
        required: true,
        options: [
          { id: 'env_quiet', label: { en: 'Quiet, solitary workspace', hi: 'शांत और एकांत जगह में' } },
          { id: 'env_team', label: { en: 'Collaborative team room with brainstorming', hi: 'टीम के साथ चर्चा और मंथन करते हुए' } },
          { id: 'env_field', label: { en: 'Moving across outdoors or project sites', hi: 'खुली जगह में या अलग-अलग साइटों पर' } },
          { id: 'env_fast', label: { en: 'High-energy, fast-paced environment', hi: 'तेज़ गति और ऊर्जा से भरे माहौल में' } },
        ],
      },
      {
        id: 'q_str_lead',
        section_id: 'sec_work_style',
        type: 'scale',
        prompt: {
          en: 'How naturally does taking the lead and coordinating people come to you?',
          hi: 'टीम का नेतृत्व और समन्वय करना आपके लिए कितना स्वाभाविक है?',
        },
        min: 1,
        max: 5,
        min_label: { en: 'Prefer supporting', hi: 'सहयोग करना पसंद है' },
        max_label: { en: 'Love leading', hi: 'नेतृत्व करना पसंद है' },
        required: true,
      },
      {
        id: 'q_ws_habits',
        section_id: 'sec_work_style',
        type: 'multi_choice',
        prompt: {
          en: 'Which habits help you succeed during complex assignments?',
          hi: 'जटिल प्रोजेक्ट्स में कौन-सी आदतें आपकी मदद करती हैं?',
        },
        required: false,
        options: [
          { id: 'hbt_check', label: { en: 'Breaking big tasks into daily checklists', hi: 'बड़े कामों को रोज़ाना की चेकलिस्ट में बाँटना' } },
          { id: 'hbt_draft', label: { en: 'Discussing early drafts with friends and mentors', hi: 'शुरुआती ड्राफ़्ट पर साथियों से चर्चा करना' } },
          { id: 'hbt_res', label: { en: 'Deep research before writing or building', hi: 'काम शुरू करने से पहले गहरा शोध करना' } },
          { id: 'hbt_trial', label: { en: 'Learning by trial, error, and rapid iteration', hi: 'प्रयोग करके और गलतियों से सीखना' } },
        ],
      },
    ],
  },
  {
    id: 'sec_values',
    title: { en: 'Values', hi: 'प्राथमिकताएँ' },
    description: { en: 'What matters most in your career', hi: 'करियर में आपके लिए सबसे अहम क्या है' },
    questions: [
      {
        id: 'q_val_risk',
        section_id: 'sec_values',
        type: 'slider',
        prompt: {
          en: 'What balance of stability versus risk do you prefer in your future?',
          hi: 'भविष्य के करियर में आप स्थिरता और जोखिम का क्या अनुपात चाहते हैं?',
        },
        min: 0,
        max: 100,
        step: 5,
        min_label: { en: 'Predictable & Stable', hi: 'सुरक्षित और स्थिर' },
        max_label: { en: 'High Growth & Entrepreneurial', hi: 'उच्च विकास व जोखिम' },
        required: true,
      },
      {
        id: 'q_val_worklife',
        section_id: 'sec_values',
        type: 'slider',
        prompt: {
          en: 'Your target balance between personal life and intense ambition:',
          hi: 'निजी समय और करियर की महत्वाकांक्षा के बीच आपका लक्ष्य:',
        },
        min: 0,
        max: 100,
        step: 5,
        min_label: { en: 'Protected Personal Time', hi: 'संतुलित जीवन' },
        max_label: { en: 'All-in Career Focus', hi: 'करियर पर पूरा ध्यान' },
        required: true,
      },
      {
        id: 'q_val_mentor',
        section_id: 'sec_values',
        type: 'text',
        prompt: {
          en: 'Who is a role model or professional whose journey inspires you?',
          hi: 'किस व्यक्ति या पेशेवर के काम से आप सबसे ज़्यादा प्रेरित होते हैं?',
        },
        required: false,
        placeholder: { en: 'e.g. APJ Abdul Kalam, Marie Curie...', hi: 'उदा. डॉ. एपीजे अब्दुल कलाम, कल्पना चावला...' },
      },
    ],
  },
  {
    id: 'sec_aspirations',
    title: { en: 'Aspirations', hi: 'भविष्य की सोच' },
    description: { en: 'Looking ahead 10 years', hi: 'अगले 10 साल की आपकी दूरदृष्टि' },
    questions: [
      {
        id: 'q_asp_dream',
        section_id: 'sec_aspirations',
        type: 'long_text',
        prompt: {
          en: 'Describe what a deeply fulfilling work day looks like for you 10 years from now:',
          hi: '10 साल बाद आपके लिए एक सार्थक और संतोषजनक कामकाजी दिन कैसा दिखेगा?',
        },
        max_length: 300,
        required: true,
        placeholder: {
          en: 'Describe what you are building, the team around you, or the impact made...',
          hi: 'वर्णन करें कि आप क्या बना रहे हैं, आपके आसपास कैसी टीम है या क्या प्रभाव पड़ा...',
        },
      },
      {
        id: 'q_asp_family',
        section_id: 'sec_aspirations',
        type: 'long_text',
        prompt: {
          en: 'What is one hope or worry you and your family often discuss about college or careers?',
          hi: 'कॉलेज या करियर को लेकर ऐसी कौन-सी उम्मीद या चिंता है जिस पर आप और परिवार बात करते हैं?',
        },
        max_length: 300,
        required: false,
        placeholder: {
          en: 'Share any financial, location, or course considerations...',
          hi: 'फीस, शहर, कॉलेज या कोर्स से जुड़ी कोई भी बात साझा करें...',
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
    return { sections: MOCK_ASSESSMENT_SECTIONS };
  }

  return request<AssessmentQuestionsResponse>(
    `/families/${encodeURIComponent(cleanCode)}/assessment/questions`,
    {
      method: 'GET',
      headers: {
        'X-Member-Token': token,
      },
    }
  );
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

  return request<AssessmentProgressResponse>(
    `/families/${encodeURIComponent(cleanCode)}/assessment/progress`,
    {
      method: 'GET',
      headers: {
        'X-Member-Token': token,
      },
    }
  );
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

  return request<SaveAnswersResponse>(
    `/families/${encodeURIComponent(cleanCode)}/assessment/answers`,
    {
      method: 'PUT',
      headers: {
        'X-Member-Token': token,
      },
      body: JSON.stringify({ answers }),
    }
  );
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

  return request<SubmitAssessmentResponse>(
    `/families/${encodeURIComponent(cleanCode)}/assessment/submit`,
    {
      method: 'POST',
      headers: {
        'X-Member-Token': token,
      },
      body: JSON.stringify({}),
    }
  );
}

// ==========================================
// Mock Parent Intake Bank
// (5 sections: money, risk, plans, hopes, perception)
// ==========================================
export const MOCK_INTAKE_SECTIONS: AssessmentSection[] = [
  {
    id: 'money',
    title: { en: 'Financial Planning', hi: 'वित्तीय योजना' },
    description: { en: 'Budget, funding sources, and financial priorities', hi: 'बजट, साधन और वित्तीय प्राथमिकताएँ' },
    questions: [
      {
        id: 'q_money_budget',
        section_id: 'money',
        type: 'single_choice',
        prompt: {
          en: 'What is your comfortable annual budget for your child’s higher education?',
          hi: 'अपने बच्चे की उच्च शिक्षा के लिए आपका सहज वार्षिक बजट क्या है?'
        },
        required: true,
        options: [
          { id: 'opt_b1', label: { en: 'Under ₹3 Lakhs / year', hi: '₹3 लाख / वर्ष से कम' } },
          { id: 'opt_b2', label: { en: '₹3 - ₹7 Lakhs / year', hi: '₹3 - ₹7 लाख / वर्ष' } },
          { id: 'opt_b3', label: { en: '₹7 - ₹15 Lakhs / year', hi: '₹7 - ₹15 लाख / वर्ष' } },
          { id: 'opt_b4', label: { en: 'Above ₹15 Lakhs / year', hi: '₹15 लाख / वर्ष से अधिक' } },
        ]
      },
      {
        id: 'q_money_source',
        section_id: 'money',
        type: 'single_choice',
        prompt: {
          en: 'What will be the primary source for funding college fees and living costs?',
          hi: 'कॉलेज फीस और रहने के खर्च का प्राथमिक साधन क्या होगा?'
        },
        required: true,
        options: [
          { id: 'opt_s1', label: { en: 'Family savings and ongoing income', hi: 'पारिवारिक बचत और नियमित आय' } },
          { id: 'opt_s2', label: { en: 'Education loan with manageable EMI', hi: 'आसान किस्तों वाला शिक्षा ऋण (Education Loan)' } },
          { id: 'opt_s3', label: { en: 'Combination of scholarships and family support', hi: 'छात्रवृत्ति (Scholarships) और पारिवारिक सहयोग' } },
          { id: 'opt_s4', label: { en: 'Selling or leveraging assets / investments', hi: 'निवेश या संपत्ति का उपयोग' } },
        ]
      },
      {
        id: 'q_money_priority',
        section_id: 'money',
        type: 'single_choice',
        prompt: {
          en: 'What is your primary financial priority when selecting a college program?',
          hi: 'कॉलेज या कोर्स चुनते समय आपकी प्राथमिक वित्तीय प्राथमिकता क्या है?'
        },
        required: true,
        options: [
          { id: 'opt_p1', label: { en: 'Quick return on investment (high early starting salary)', hi: 'लागत की जल्द भरपाई (शुरुआती अच्छा वेतन)' } },
          { id: 'opt_p2', label: { en: 'Minimizing debt and keeping upfront expenses low', hi: 'कर्ज से बचना और शुरुआती खर्च कम रखना' } },
          { id: 'opt_p3', label: { en: 'Institutional prestige and brand value regardless of cost', hi: 'संस्थान की प्रतिष्ठा और ब्रांड वैल्यू, चाहे लागत जो भी हो' } },
          { id: 'opt_p4', label: { en: 'Long-term career ceiling rather than short-term payback', hi: 'दीर्घकालिक करियर विकास, न कि सिर्फ़ तात्कालिक लाभ' } },
        ]
      }
    ]
  },
  {
    id: 'risk',
    title: { en: 'Risk & Stability', hi: 'स्थिरता और जोखिम' },
    description: { en: 'Career security, relocation, and preparation timelines', hi: 'करियर सुरक्षा, स्थानांतरण और तैयारी की अवधि' },
    questions: [
      {
        id: 'q_risk_security',
        section_id: 'risk',
        type: 'single_choice',
        prompt: {
          en: 'How important is job stability versus rapid financial growth in your child’s career?',
          hi: 'बच्चे के करियर में नौकरी की स्थिरता बनाम तेज़ वित्तीय तरक्की कितनी महत्वपूर्ण है?'
        },
        required: true,
        options: [
          { id: 'opt_sec1', label: { en: 'Stability is essential (Govt, PSU, or established enterprise)', hi: 'स्थिरता सबसे ज़रूरी है (सरकारी, PSU या स्थापित संस्थान)' } },
          { id: 'opt_sec2', label: { en: 'Balanced (stable industry with good corporate promotion track)', hi: 'संतुलित (स्थिर उद्योग और अच्छी पदोन्नति के अवसर)' } },
          { id: 'opt_sec3', label: { en: 'Growth-first (open to startups, tech, and fast-changing sectors)', hi: 'विकास प्राथमिकता (स्टार्टअप्स, तकनीक और नए क्षेत्र)' } },
          { id: 'opt_sec4', label: { en: 'Entrepreneurial (fully comfortable with high risk / reward)', hi: 'उद्यमिता (उच्च जोखिम और बड़े अवसरों के लिए तैयार)' } },
        ]
      },
      {
        id: 'q_risk_location',
        section_id: 'risk',
        type: 'single_choice',
        prompt: {
          en: 'What is your stance on your child relocating for higher studies or work?',
          hi: 'उच्च शिक्षा या नौकरी के लिए बच्चे के बाहर जाने पर आपका क्या विचार है?'
        },
        required: true,
        options: [
          { id: 'opt_loc1', label: { en: 'Prefer staying within our home city / region', hi: 'अपने शहर या आसपास के क्षेत्र में रहना पसंद करेंगे' } },
          { id: 'opt_loc2', label: { en: 'Any major metropolitan hub across India is welcome', hi: 'भारत के किसी भी बड़े शहर में जाने के लिए पूरी सहमति है' } },
          { id: 'opt_loc3', label: { en: 'Open to studies and careers abroad if feasible', hi: 'यदि संभव हो तो विदेश जाकर पढ़ाई या काम करने के लिए तैयार' } },
        ]
      },
      {
        id: 'q_risk_gap',
        section_id: 'risk',
        type: 'single_choice',
        prompt: {
          en: 'How comfortable are you with a drop year (gap year) for competitive exam prep?',
          hi: 'प्रतियोगी परीक्षा की तैयारी के लिए ड्रॉप ईयर (गैप ईयर) लेने पर आपकी क्या राय है?'
        },
        required: true,
        options: [
          { id: 'opt_gap1', label: { en: 'Strictly no gap year; continuous admission is preferred', hi: 'ड्रॉप ईयर नहीं लेना चाहिए; सीधे प्रवेश बेहतर है' } },
          { id: 'opt_gap2', label: { en: 'One dedicated drop year is acceptable for top tier exams', hi: 'शीर्ष परीक्षाओं के लिए एक साल का ड्रॉप स्वीकार्य है' } },
          { id: 'opt_gap3', label: { en: 'Flexible if there is a structured coaching plan and discipline', hi: 'यदि सुनियोजित तैयारी और अनुशासन हो तो कोई आपत्ति नहीं' } },
        ]
      }
    ]
  },
  {
    id: 'plans',
    title: { en: 'Academic Path & Timeline', hi: 'शैक्षणिक योजना और समय' },
    description: { en: 'Degree structures and postgraduate expectations', hi: 'डिग्री का स्वरूप और स्नातकोत्तर की उम्मीदें' },
    questions: [
      {
        id: 'q_plans_degree',
        section_id: 'plans',
        type: 'single_choice',
        prompt: {
          en: 'What degree path do you envision for your child right after school?',
          hi: 'स्कूल के बाद आप अपने बच्चे के लिए किस प्रकार की डिग्री की उम्मीद करते हैं?'
        },
        required: true,
        options: [
          { id: 'opt_deg1', label: { en: 'Standard 3-4 year Bachelor’s (B.Tech, B.Sc, B.Com, BA)', hi: 'पारंपरिक 3-4 वर्षीय स्नातक डिग्री (B.Tech, B.Sc, B.Com, BA)' } },
          { id: 'opt_deg2', label: { en: 'Integrated 5-year Dual Degree (B.Tech+M.Tech, BBA+MBA, Law)', hi: '5 वर्षीय एकीकृत दोहरी डिग्री (B.Tech+M.Tech, BBA+MBA, लॉ)' } },
          { id: 'opt_deg3', label: { en: 'Professional certification / vocational specialization', hi: 'व्यावसायिक या विशेष सर्टिफिकेशन कार्यक्रम' } },
        ]
      },
      {
        id: 'q_plans_postgrad',
        section_id: 'plans',
        type: 'single_choice',
        prompt: {
          en: 'What is your expectation regarding postgraduate studies (Masters / MBA)?',
          hi: 'स्नातकोत्तर (Masters / MBA) की पढ़ाई को लेकर आपकी क्या अपेक्षा है?'
        },
        required: true,
        options: [
          { id: 'opt_pg1', label: { en: 'Should start working immediately after graduation', hi: 'स्नातक पूरा होते ही नौकरी शुरू करनी चाहिए' } },
          { id: 'opt_pg2', label: { en: 'Work 2-3 years first, then pursue a specialized Masters / MBA', hi: 'पहले 2-3 साल काम करे, फिर मास्टर्स या एमबीए करे' } },
          { id: 'opt_pg3', label: { en: 'Complete Masters / higher degrees back-to-back before work', hi: 'नौकरी से पहले मास्टर्स या उच्च शिक्षा पूरी करे' } },
        ]
      }
    ]
  },
  {
    id: 'hopes',
    title: { en: 'Aspirations & Hopes', hi: 'उम्मीदें और आकांक्षाएँ' },
    description: { en: 'Fields of pride, family involvement, and personal wishes', hi: 'पसंदीदा क्षेत्र, पारिवारिक सहयोग और व्यक्तिगत उम्मीदें' },
    questions: [
      {
        id: 'q_hopes_fields',
        section_id: 'hopes',
        type: 'multi_choice',
        max_select: 3,
        prompt: {
          en: 'Which sectors or career paths would you be proudest to see your child pursue? (Select up to 3)',
          hi: 'किन क्षेत्रों या करियर में बच्चे को आगे बढ़ते देख आपको सबसे ज़्यादा गर्व होगा? (अधिकतम 3 चुनें)'
        },
        required: true,
        options: [
          { id: 'fld_tech', label: { en: 'Engineering, AI & Technology', hi: 'इंजीनियरिंग, एआई और तकनीक' } },
          { id: 'fld_med', label: { en: 'Medicine, Surgery & Healthcare', hi: 'चिकित्सा और स्वास्थ्य सेवा' } },
          { id: 'fld_gov', label: { en: 'Civil Services, Defense & Public Administration', hi: 'सिविल सेवा, रक्षा और लोक प्रशासन' } },
          { id: 'fld_biz', label: { en: 'Business Management, Consulting & Finance', hi: 'बिजनेस मैनेजमेंट, कंसल्टिंग और फाइनेंस' } },
          { id: 'fld_law', label: { en: 'Law, Judiciary & Legal Practice', hi: 'कानून और न्यायपालिका' } },
          { id: 'fld_art', label: { en: 'Design, Architecture & Creative Media', hi: 'डिजाइन, वास्तुकला और मीडिया' } },
          { id: 'fld_sci', label: { en: 'Academic Research & Pure Sciences', hi: 'शोध और वैज्ञानिक अनुसंधान' } },
        ]
      },
      {
        id: 'q_hopes_support',
        section_id: 'hopes',
        type: 'multi_choice',
        prompt: {
          en: 'How are you most excited to support them on this journey? (Optional)',
          hi: 'इस यात्रा में आप किस प्रकार उनका सहयोग करने के लिए सबसे उत्सुक हैं? (वैकल्पिक)'
        },
        required: false,
        options: [
          { id: 'sup_mentor', label: { en: 'Mentorship, industry guidance and professional network', hi: 'मार्गदर्शन और व्यावसायिक नेटवर्क से जोड़ना' } },
          { id: 'sup_moral', label: { en: 'Unconditional emotional and motivational encouragement', hi: 'सकारात्मक माहौल और भावनात्मक संबल' } },
          { id: 'sup_finance', label: { en: 'Financial backup and safety cushion', hi: 'आर्थिक सहयोग और सुरक्षा' } },
          { id: 'sup_indep', label: { en: 'Giving full autonomy to make and learn from their choices', hi: 'स्वतंत्रता और अपने निर्णय खुद लेने का अवसर' } },
        ]
      },
      {
        id: 'q_hopes_personal',
        section_id: 'hopes',
        type: 'long_text',
        max_length: 300,
        prompt: {
          en: 'What is your biggest personal hope or message for your child’s future? (Optional)',
          hi: 'अपने बच्चे के भविष्य के लिए आपकी सबसे बड़ी व्यक्तिगत उम्मीद या संदेश क्या है? (वैकल्पिक)'
        },
        required: false,
        placeholder: {
          en: 'Share your hopes for their happiness, independence, resilience...',
          hi: 'उनकी खुशी, आत्मनिर्भरता और सफलता को लेकर अपनी भावनाएँ साझा करें...'
        }
      }
    ]
  },
  {
    id: 'perception',
    title: { en: 'Strengths & Perception', hi: 'क्षमता और समझ' },
    description: { en: 'Observed strengths and natural inclinations', hi: 'बच्चे की ताकत और स्वाभाविक प्रवृत्तियाँ' },
    questions: [
      {
        id: 'q_perc_strength',
        section_id: 'perception',
        type: 'single_choice',
        prompt: {
          en: 'Where do you observe your child naturally shining the brightest?',
          hi: 'आपके अनुसार आपका बच्चा स्वाभाविक रूप से किस चीज़ में सबसे बेहतर है?'
        },
        required: true,
        options: [
          { id: 'str_logic', label: { en: 'Logical reasoning, quantitative calculations and problem-solving', hi: 'तार्किक सोच, गणितीय गणना और समस्याओं का हल' } },
          { id: 'str_people', label: { en: 'Communication, empathy and connecting with people', hi: 'संवाद, सहानुभूति और लोगों से जुड़ाव' } },
          { id: 'str_creative', label: { en: 'Artistic creativity, innovative design and out-of-box ideas', hi: 'रचनात्मकता, कला और नए विचार' } },
          { id: 'str_practical', label: { en: 'Practical execution, organizing tasks and building physical things', hi: 'व्यावहारिक काम, चीज़ें बनाना और प्रबंधन' } },
        ]
      },
      {
        id: 'q_perc_pressure',
        section_id: 'perception',
        type: 'single_choice',
        prompt: {
          en: 'How does your child typically respond during stressful exam or competition periods?',
          hi: 'परीक्षा या तनावपूर्ण समय में आपका बच्चा आमतौर पर कैसा व्यवहार करता है?'
        },
        required: true,
        options: [
          { id: 'prs_calm', label: { en: 'Remains calm, methodical and sticks to a consistent schedule', hi: 'शांत रहता है और योजनाबद्ध तरीके से पढ़ाई करता है' } },
          { id: 'prs_burst', label: { en: 'Works in energetic, intense bursts closer to deadlines', hi: 'आखिरी दिनों में बहुत ऊर्जा और एकाग्रता के साथ काम करता है' } },
          { id: 'prs_anxious', label: { en: 'Experiences anxiety and thrives best with regular parent reassurance', hi: 'तनाव महसूस करता है और प्रोत्साहन से बेहतर करता है' } },
        ]
      },
      {
        id: 'q_perc_discussion',
        section_id: 'perception',
        type: 'single_choice',
        prompt: {
          en: 'How are major educational and career choices currently discussed at home?',
          hi: 'घर पर पढ़ाई और करियर से जुड़े बड़े फैसले किस तरह लिए जाते हैं?'
        },
        required: true,
        options: [
          { id: 'disc_open', label: { en: 'Open equal discussions where everyone shares viewpoints freely', hi: 'खुली बातचीत जहाँ सभी अपनी राय खुलकर रखते हैं' } },
          { id: 'disc_guided', label: { en: 'Parents provide structured guidance and shortlisted choices', hi: 'अभिभावक सही दिशा और विकल्प सुझाते हैं' } },
          { id: 'disc_student', label: { en: 'Child takes full ownership and parents support their lead', hi: 'बच्चा खुद निर्णय लेता है और परिवार उसका साथ देता है' } },
        ]
      }
    ]
  }
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
    return { sections: MOCK_INTAKE_SECTIONS };
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
      return { sections: MOCK_INTAKE_SECTIONS };
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
