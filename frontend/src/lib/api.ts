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

export interface FamilyStatusResponse {
  family_code: string;
  linked: boolean;
  you: {
    role: Role;
    name: string;
  };
  partner: {
    role: Role;
    name: string;
  } | null;
  expires_at: string;
}

export interface ApiErrorShape {
  error: {
    code: string;
    message: string;
  };
}

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number = 400) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

const getApiBaseUrl = (): string => {
  return process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
};

const isMockEnabled = (): boolean => {
  return process.env.NEXT_PUBLIC_USE_MOCK === 'true';
};

// Mock storage helper using sessionStorage when available
interface MockFamilyRecord {
  code: string;
  creatorRole: Role;
  creatorName: string;
  creatorLang: Language;
  createdAt: number;
  joinedRole?: Role;
  joinedName?: string;
}

const inMemoryMockFamilies: Record<string, MockFamilyRecord> = {};

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

    try {
      const data = (await response.json()) as ApiErrorShape;
      if (data && data.error) {
        errorCode = data.error.code || errorCode;
        errorMessage = data.error.message || errorMessage;
      }
    } catch {
      // Body was not JSON
    }

    throw new ApiError(errorCode, errorMessage, response.status);
  }

  return (await response.json()) as T;
}

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

    // Turns linked after ~6 seconds per specification
    const elapsed = existing ? Date.now() - existing.createdAt : 7000;
    const isLinked = elapsed >= 6000 || !!existing?.joinedName;

    return {
      family_code: cleanCode,
      linked: isLinked,
      you: {
        role: myRole,
        name: myName,
      },
      partner: isLinked
        ? {
            role: partnerRole,
            name: existing?.joinedName || defaultPartnerName,
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
