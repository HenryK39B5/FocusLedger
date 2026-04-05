from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.core.config import Settings
from src.integrations.wechat_ingestion.core.wechat_funcs import WeChatFuncs
from src.models import ArticleSource, SourceCredential
from src.schemas.content import SourceCredentialCheckRead


@dataclass
class ParsedCredentialLink:
    raw_link: str
    biz: str
    uin: str
    key: str
    pass_ticket: str
    appmsg_token: str
    session_us: str
    scene: str
    username: str
    raw_query: dict[str, str]
    provider: str = "manual"


class CredentialProvider:
    provider_name = "base"

    def parse(self, raw_link: str) -> ParsedCredentialLink:
        raise NotImplementedError


class ManualCredentialProvider(CredentialProvider):
    provider_name = "manual"

    def __init__(self, settings: Settings):
        self.wechat = WeChatFuncs(timeout=settings.request_timeout_seconds, verify_ssl=settings.wechat_verify_ssl)

    def parse(self, raw_link: str) -> ParsedCredentialLink:
        if "profile_ext" not in raw_link:
            raise ValueError("这里需要粘贴完整的 profile_ext 链接。")
        token = self.wechat.parse_token_link(raw_link)
        if not token:
            raise ValueError("无法解析来源凭据中的关键参数，请重新复制完整的 profile_ext 链接。")
        return ParsedCredentialLink(
            raw_link=raw_link.strip(),
            biz=token.biz,
            uin=token.uin,
            key=token.key,
            pass_ticket=token.pass_ticket,
            appmsg_token=token.appmsg_token,
            session_us=token.session_us,
            scene=token.scene,
            username=token.username,
            raw_query=token.raw_query or {},
            provider=self.provider_name,
        )


class SourceCredentialService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = ManualCredentialProvider(settings)
        self.wechat = WeChatFuncs(timeout=settings.request_timeout_seconds, verify_ssl=settings.wechat_verify_ssl)

    def parse_link(self, raw_link: str, provider_name: str = "manual") -> ParsedCredentialLink:
        parsed = self.provider.parse(raw_link)
        parsed.provider = provider_name
        return parsed

    def upsert_credential(
        self,
        db: Session,
        source: ArticleSource,
        raw_link: str,
        *,
        provider_name: str,
        validate_after_update: bool = True,
    ) -> tuple[SourceCredential, SourceCredentialCheckRead | None]:
        parsed = self.parse_link(raw_link, provider_name=provider_name)
        if parsed.biz != source.biz:
            raise ValueError("这条来源凭据对应的公众号与当前来源不一致，请确认 __biz 是否匹配。")

        credential = source.credential or SourceCredential(source_id=source.id)
        credential.provider = parsed.provider
        credential.raw_link = parsed.raw_link
        credential.token_biz = parsed.biz
        credential.uin = parsed.uin
        credential.key = parsed.key
        credential.pass_ticket = parsed.pass_ticket
        credential.appmsg_token = parsed.appmsg_token or None
        credential.session_us = parsed.session_us or None
        credential.scene = parsed.scene or None
        credential.username = parsed.username or None
        credential.raw_query = parsed.raw_query
        if source.credential is None:
            credential.source = source
            db.add(credential)

        source.credential_status = "unknown"
        source.last_error_code = None
        source.last_error_message = None
        db.flush()

        check_result = self.verify_credential(db, source) if validate_after_update else None
        return credential, check_result

    def upsert_manual_credential(
        self,
        db: Session,
        source: ArticleSource,
        raw_link: str,
        validate_after_update: bool = True,
    ) -> tuple[SourceCredential, SourceCredentialCheckRead | None]:
        return self.upsert_credential(
            db,
            source,
            raw_link,
            provider_name="manual",
            validate_after_update=validate_after_update,
        )

    def verify_credential(self, db: Session, source: ArticleSource) -> SourceCredentialCheckRead:
        now = datetime.now(timezone.utc)

        if not source.credential:
            source.credential_status = "missing"
            source.last_verified_at = now
            source.last_sync_failed_at = now
            source.last_error_code = "missing_credential"
            source.last_error_message = "当前来源还没有可用的 profile_ext 凭据。"
            db.flush()
            return SourceCredentialCheckRead(
                source_id=source.id,
                source_name=source.name,
                valid=False,
                credential_status=source.credential_status,
                needs_refresh=True,
                error_code=source.last_error_code,
                error_message=source.last_error_message,
                last_verified_at=source.last_verified_at,
                message="当前来源缺少可用凭据，请先更新来源链接。",
            )

        check = self.wechat.verify_token_link(source.credential.raw_link)
        source.last_verified_at = now
        source.last_error_code = check.error_code
        source.last_error_message = check.error_message

        if check.valid:
            source.credential_status = "valid"
            source.last_error_code = None
            source.last_error_message = None
        elif check.needs_refresh:
            source.credential_status = "refresh_required"
        elif check.error_code == "invalid_token":
            source.credential_status = "invalid"

        db.flush()
        return SourceCredentialCheckRead(
            source_id=source.id,
            source_name=source.name,
            valid=check.valid,
            credential_status=source.credential_status,
            needs_refresh=check.needs_refresh,
            error_code=check.error_code,
            error_message=check.error_message,
            last_verified_at=source.last_verified_at,
            message=check.message,
        )

    def record_sync_result(
        self,
        db: Session,
        source: ArticleSource,
        *,
        success: bool,
        failure_reason_category: str | None = None,
        error_message: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        if success:
            source.credential_status = "valid"
            source.last_verified_at = now
            source.last_sync_succeeded_at = now
            source.last_error_code = None
            source.last_error_message = None
            db.flush()
            return

        if failure_reason_category == "no_articles_in_range":
            source.credential_status = "valid"
            source.last_verified_at = now
            source.last_error_code = None
            source.last_error_message = None
            db.flush()
            return

        source.last_sync_failed_at = now
        if failure_reason_category:
            source.last_error_code = failure_reason_category
        if error_message:
            source.last_error_message = error_message

        if failure_reason_category in {
            "no_session",
            "empty_response",
            "credential_refresh_timeout",
            "incomplete_capture",
            "fiddler_conflict",
            "fiddler_start_failed",
        }:
            source.credential_status = "refresh_required"
            source.last_verified_at = now
        elif failure_reason_category == "invalid_token":
            source.credential_status = "invalid"
            source.last_verified_at = now

        db.flush()
