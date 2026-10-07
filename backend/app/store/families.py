import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings
from app.schemas.families import LangEnum, RoleEnum

FAMILY_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
FAMILY_CODE_LENGTH = 6


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def format_iso8601(dt: datetime) -> str:
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.isoformat()


def normalize_family_code(code: str) -> str:
    return code.upper().replace(" ", "").replace("-", "")


@dataclass
class MemberRecord:
    token: str
    role: RoleEnum
    name: str
    lang: LangEnum
    joined_at: datetime


@dataclass
class FamilyRecord:
    family_code: str
    created_at: datetime
    expires_at: datetime
    members: list[MemberRecord] = field(default_factory=list)

    @property
    def creator(self) -> MemberRecord:
        return self.members[0]

    def get_member_by_role(self, role: RoleEnum) -> Optional[MemberRecord]:
        for m in self.members:
            if m.role == role:
                return m
        return None

    def get_member_by_token(self, token: str) -> Optional[MemberRecord]:
        for m in self.members:
            if m.token == token:
                return m
        return None

    @property
    def open_role(self) -> Optional[RoleEnum]:
        if len(self.members) >= 2:
            return None
        existing_role = self.members[0].role
        return RoleEnum.PARENT if existing_role == RoleEnum.STUDENT else RoleEnum.STUDENT


class FamilyStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._families: dict[str, FamilyRecord] = {}

    def _purge_expired_locked(self, current_time: datetime) -> None:
        expired = [
            code
            for code, fam in self._families.items()
            if fam.expires_at <= current_time
        ]
        for code in expired:
            del self._families[code]

    def _get_ttl(self) -> timedelta:
        return timedelta(minutes=settings.family_ttl_minutes)

    def create_family(
        self, role: RoleEnum, name: str, lang: LangEnum
    ) -> tuple[FamilyRecord, MemberRecord]:
        with self._lock:
            now = now_utc()
            self._purge_expired_locked(now)

            # Generate unique code from contract alphabet
            for _ in range(100):
                code = "".join(
                    secrets.choice(FAMILY_CODE_ALPHABET)
                    for _ in range(FAMILY_CODE_LENGTH)
                )
                if code not in self._families:
                    break
            else:
                raise RuntimeError("Failed to generate unique family code")

            member = MemberRecord(
                token=secrets.token_urlsafe(24),
                role=role,
                name=name,
                lang=lang,
                joined_at=now,
            )

            family = FamilyRecord(
                family_code=code,
                created_at=now,
                expires_at=now + self._get_ttl(),
                members=[member],
            )
            self._families[code] = family
            return family, member

    def get_family_for_preview(
        self, raw_code: str
    ) -> Optional[FamilyRecord]:
        code = normalize_family_code(raw_code)
        with self._lock:
            now = now_utc()
            fam = self._families.get(code)
            if fam is None:
                return None
            if fam.expires_at <= now:
                del self._families[code]
                return None
            return fam

    def join_family(
        self, raw_code: str, role: RoleEnum, name: str, lang: LangEnum
    ) -> tuple[str, Optional[FamilyRecord], Optional[MemberRecord], Optional[MemberRecord]]:
        code = normalize_family_code(raw_code)
        with self._lock:
            now = now_utc()
            fam = self._families.get(code)
            if fam is None:
                return "family_not_found", None, None, None
            if fam.expires_at <= now:
                del self._families[code]
                return "family_not_found", None, None, None

            if len(fam.members) >= 2:
                return "family_full", None, None, None

            if fam.get_member_by_role(role) is not None:
                return "role_taken", None, None, None

            new_member = MemberRecord(
                token=secrets.token_urlsafe(24),
                role=role,
                name=name,
                lang=lang,
                joined_at=now,
            )
            partner = fam.members[0]
            fam.members.append(new_member)
            return "ok", fam, new_member, partner

    def get_family_status(
        self, raw_code: str, token: str
    ) -> tuple[str, Optional[FamilyRecord], Optional[MemberRecord], Optional[MemberRecord]]:
        code = normalize_family_code(raw_code)
        with self._lock:
            now = now_utc()
            fam = self._families.get(code)
            if fam is None:
                return "family_not_found", None, None, None
            if fam.expires_at <= now:
                del self._families[code]
                return "family_not_found", None, None, None

            you = fam.get_member_by_token(token)
            if you is None:
                return "invalid_token", None, None, None

            # Reset sliding window on successful status call
            fam.expires_at = now + self._get_ttl()

            partner = next((m for m in fam.members if m.token != token), None)
            return "ok", fam, you, partner

    def clear(self) -> None:
        with self._lock:
            self._families.clear()


family_store = FamilyStore()
