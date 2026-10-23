"""Bounded HTTPS source downloads with connection-time destination validation.

A dedicated connector is intentional: Home Assistant's shared session connector
cannot use this resolver. Validation happens in the resolver used by the actual
socket connection, rather than in a vulnerable separate DNS preflight check.
"""

import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass
from hashlib import sha256
from urllib.parse import urlsplit
from zoneinfo import ZoneInfoNotFoundError

from aiohttp import (
    ClientError,
    ClientSession,
    ClientTimeout,
    DummyCookieJar,
    TCPConnector,
)
from aiohttp.abc import AbstractResolver, ResolveResult
from aiohttp.resolver import DefaultResolver
from yarl import URL

from .import_model import MAX_PDF_BYTES

MAX_CSV_BYTES = 512 * 1024
MAX_REDIRECTS = 3
TOTAL_TIMEOUT = 30
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 10
MAX_URL_LENGTH = 2048
MAX_VALIDATOR_LENGTH = 512
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_LOCAL_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".home",
    ".lan",
    ".onion",
    ".invalid",
    ".test",
    ".arpa",
)
_TRANSITION_NETWORKS = tuple(
    ipaddress.ip_network(value)
    for value in ("64:ff9b::/96", "64:ff9b:1::/48", "2002::/16", "2001::/32")
)


class DownloadError(ValueError):
    """A fixed, URL-free error that is safe for UI status and logs."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class DownloadResult:
    """Downloaded bytes or a valid conditional not-modified response."""

    content: bytes | None
    media_type: str
    etag: str | None
    last_modified: str | None
    sha256: str | None
    not_modified: bool = False


def _public_address(value: str) -> None:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        raise DownloadError(
            "unsafe_destination", "The source resolved to an invalid address"
        ) from None
    if (
        not address.is_global
        or address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
        or getattr(address, "is_site_local", False)
        or getattr(address, "ipv4_mapped", None) is not None
        or any(
            address in network
            for network in _TRANSITION_NETWORKS
            if address.version == network.version
        )
    ):
        raise DownloadError(
            "unsafe_destination", "Only public Internet source destinations are allowed"
        )


def _validate_host(host: str) -> None:
    if "%" in host:
        raise DownloadError(
            "unsafe_destination", "Scoped source addresses are not allowed"
        )
    try:
        ipaddress.ip_address(host)
    except ValueError:
        name = host.rstrip(".").lower()
        if (
            len(name) > 253
            or "." not in name
            or name.endswith(_LOCAL_SUFFIXES)
            or any(
                not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                for label in name.split(".")
            )
        ):
            raise DownloadError(
                "unsafe_destination", "Enter a public Internet source hostname"
            )
    else:
        _public_address(host)


def _validated_url(value: str) -> URL:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_URL_LENGTH
        or any(ord(character) <= 32 or ord(character) == 127 for character in value)
        or "\\" in value
        or "#" in value
    ):
        raise DownloadError("invalid_url", "Enter a valid HTTPS timetable URL")
    try:
        if "@" in urlsplit(value).netloc:
            raise ValueError
        url = URL(value)
        if (
            url.scheme != "https"
            or not url.raw_host
            or url.port != 443
            or url.user is not None
            or url.password is not None
            or url.fragment
        ):
            raise ValueError
        _validate_host(url.raw_host)
    except DownloadError:
        raise
    except (
        ZoneInfoNotFoundError,
        ValueError,
        TypeError,
    ):
        raise DownloadError(
            "invalid_url", "Use HTTPS on port 443 without credentials or a fragment"
        ) from None
    return url


def validate_url(url: str) -> str:
    """Validate syntax and literal destinations without a separate DNS lookup."""
    return str(_validated_url(url))


class PublicResolver(AbstractResolver):
    """Return only validated IPs to the connector that opens the connection."""

    def __init__(self, resolver: AbstractResolver | None = None) -> None:
        self._resolver = resolver if resolver is not None else DefaultResolver()

    async def resolve(
        self,
        host: str,
        port: int = 0,
        family: socket.AddressFamily = socket.AF_INET,  # pylint: disable=no-member
    ) -> list[ResolveResult]:
        _validate_host(host)
        answers = await self._resolver.resolve(host, port, family)
        if not answers:
            raise DownloadError(
                "unsafe_destination", "The source has no usable public address"
            )
        for answer in answers:
            _public_address(answer["host"])
        return answers

    async def close(self) -> None:
        await self._resolver.close()


def _header_validator(value: str | None) -> str | None:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_VALIDATOR_LENGTH
        or any(not 32 <= ord(character) <= 126 for character in value)
    ):
        return None
    return value


def _content_type(response, media_type: str) -> None:
    content_type = (
        response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    )
    allowed = (
        {"application/pdf"}
        if media_type == "pdf"
        else {"text/csv", "application/csv", "text/plain"}
    )
    if content_type not in allowed:
        raise DownloadError(
            "invalid_content_type", "The source response has an unsupported file type"
        )
    encoding = response.headers.get("Content-Encoding", "identity").strip().lower()
    if encoding not in {"", "identity"}:
        raise DownloadError(
            "unsupported_encoding", "Compressed timetable responses are not supported"
        )


def _verify_signature(content: bytes, media_type: str) -> None:
    if not content:
        raise DownloadError("invalid_content", "The timetable source is empty")
    if media_type == "pdf":
        if (
            not re.match(rb"%PDF-[12]\.[0-9]", content)
            or b"%%EOF" not in content[-1024:]
        ):
            raise DownloadError(
                "invalid_content", "The response is not a complete supported PDF file"
            )
        return
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise DownloadError(
            "invalid_content", "CSV sources must be UTF-8 text"
        ) from None
    if (
        any(ord(character) < 32 and character not in "\r\n\t" for character in text)
        or re.match(r"\s*<(?:!doctype|html|head|body|\?xml)\b", text, re.IGNORECASE)
        or content.startswith(b"%PDF-")
    ):
        raise DownloadError(
            "invalid_content", "The response does not contain supported CSV text"
        )


async def async_download(
    url: str,
    *,
    media_type: str = "pdf",
    etag: str | None = None,
    last_modified: str | None = None,
) -> DownloadResult:
    """Download a public HTTPS source, never automatically following redirects.

    Error messages deliberately omit URLs, hostnames, response bodies and original
    transport exceptions because source URLs can include private query parameters.
    """
    current = _validated_url(url)
    if media_type not in {"pdf", "csv"}:
        raise DownloadError("invalid_source_type", "Select a PDF or CSV source")
    headers = {
        "Accept": "application/pdf"
        if media_type == "pdf"
        else "text/csv, application/csv, text/plain",
        "Accept-Encoding": "identity",
        "User-Agent": "HomeAssistant SalahTimetable",
    }
    for header, value in (
        ("If-None-Match", etag),
        ("If-Modified-Since", last_modified),
    ):
        if value is not None:
            if _header_validator(value) is None:
                raise DownloadError(
                    "invalid_validator", "The saved HTTP source validator is invalid"
                )
            headers[header] = value
    limit = MAX_PDF_BYTES if media_type == "pdf" else MAX_CSV_BYTES
    timeout = ClientTimeout(
        total=None,
        connect=CONNECT_TIMEOUT,
        sock_connect=CONNECT_TIMEOUT,
        sock_read=READ_TIMEOUT,
    )
    resolver = PublicResolver()
    connector = TCPConnector(
        resolver=resolver, use_dns_cache=False, force_close=True, ssl=True, limit=2
    )
    try:
        async with asyncio.timeout(TOTAL_TIMEOUT):
            async with ClientSession(
                connector=connector,
                connector_owner=True,
                timeout=timeout,
                auto_decompress=False,
                trust_env=False,
                cookie_jar=DummyCookieJar(),
            ) as session:
                for redirect_count in range(MAX_REDIRECTS + 1):
                    async with session.get(
                        current, headers=headers, allow_redirects=False
                    ) as response:
                        if response.status in _REDIRECT_STATUSES:
                            if redirect_count == MAX_REDIRECTS:
                                raise DownloadError(
                                    "too_many_redirects",
                                    "The timetable source redirected too many times",
                                )
                            location = response.headers.get("Location")
                            if (
                                not location
                                or any(
                                    ord(character) <= 32 or ord(character) == 127
                                    for character in location
                                )
                                or "\\" in location
                            ):
                                raise DownloadError(
                                    "invalid_redirect",
                                    "The timetable server returned an invalid redirect",
                                )
                            try:
                                if "@" in urlsplit(location).netloc or "#" in location:
                                    raise ValueError
                                target = _validated_url(
                                    str(current.join(URL(location)))
                                )
                            except (
                                ValueError,
                                TypeError,
                            ):
                                raise DownloadError(
                                    "unsafe_redirect",
                                    "The timetable server redirected to an unsafe destination",
                                ) from None
                            if current.origin() != target.origin():
                                headers.pop("If-None-Match", None)
                                headers.pop("If-Modified-Since", None)
                            current = target
                            continue
                        if response.status == 304:
                            if not (
                                "If-None-Match" in headers
                                or "If-Modified-Since" in headers
                            ):
                                raise DownloadError(
                                    "unexpected_not_modified",
                                    "The server returned an unexpected not-modified response",
                                )
                            return DownloadResult(
                                None,
                                media_type,
                                _header_validator(response.headers.get("ETag")) or etag,
                                _header_validator(response.headers.get("Last-Modified"))
                                or last_modified,
                                None,
                                True,
                            )
                        if response.status != 200:
                            raise DownloadError(
                                "http_error",
                                f"The timetable server returned HTTP {response.status}",
                            )
                        _content_type(response, media_type)
                        content_length = response.headers.get("Content-Length")
                        if content_length is not None:
                            if (
                                not content_length.isascii()
                                or not content_length.isdigit()
                            ):
                                raise DownloadError(
                                    "invalid_content_length",
                                    "The timetable server returned an invalid file size",
                                )
                            if len(content_length) > 12 or int(content_length) > limit:
                                raise DownloadError(
                                    "too_large",
                                    "The timetable download exceeds the allowed size",
                                )
                        chunks = []
                        size = 0
                        async for chunk in response.content.iter_chunked(64 * 1024):
                            size += len(chunk)
                            if size > limit:
                                raise DownloadError(
                                    "too_large",
                                    "The timetable download exceeds the allowed size",
                                )
                            chunks.append(chunk)
                        content = b"".join(chunks)
                        _verify_signature(content, media_type)
                        return DownloadResult(
                            content,
                            media_type,
                            _header_validator(response.headers.get("ETag")),
                            _header_validator(response.headers.get("Last-Modified")),
                            sha256(content).hexdigest(),
                        )
    except DownloadError:
        raise
    except TimeoutError:
        raise DownloadError("timeout", "The timetable download timed out") from None
    except (
        ClientError,
        OSError,
        ValueError,
    ):
        raise DownloadError(
            "connection_failed", "The timetable source could not be reached securely"
        ) from None
    finally:
        await connector.close()
        await resolver.close()
    raise DownloadError("http_error", "The timetable source could not be downloaded")
