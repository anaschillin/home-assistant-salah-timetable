"""Downloader boundaries and real connector DNS resolution, without the Internet."""

import asyncio
import socket
from hashlib import sha256
from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientConnectionError, DummyCookieJar

from custom_components.salah_timetable import download

PUBLIC_URL = "https://mosque.example.org/timetable.pdf?private=value"
PDF = b"%PDF-1.7\nfixture\n%%EOF\n"
CSV = b"Date,Fajr Begin\n2026-10-21,05:45\n"


class FakeContent:
    def __init__(self, chunks, delay=0):
        self.chunks = chunks
        self.delay = delay

    async def iter_chunked(self, size):
        assert size == 64 * 1024
        for chunk in self.chunks:
            if self.delay:
                await asyncio.sleep(self.delay)
            if isinstance(chunk, BaseException):
                raise chunk
            yield chunk


class Response:
    def __init__(self, status=200, *, body=PDF, headers=None, chunks=None, delay=0):
        self.status = status
        self.headers = (
            headers if headers is not None else {"Content-Type": "application/pdf"}
        )
        self.content = FakeContent([body] if chunks is None else chunks, delay)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


@pytest.fixture
def transport(monkeypatch):
    """Keep a real connector to inspect security defaults, fake only HTTP I/O."""
    responses = []
    calls = []
    session_arguments = []
    connector_arguments = []
    original_connector = download.TCPConnector

    def connector_factory(**kwargs):
        connector_arguments.append(kwargs)
        return original_connector(**kwargs)

    class Session:
        def __init__(self, **kwargs):
            session_arguments.append(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def get(self, url, **kwargs):
            calls.append((str(url), {**kwargs, "headers": dict(kwargs["headers"])}))
            response = responses.pop(0)
            if isinstance(response, BaseException):
                raise response
            return response

    monkeypatch.setattr(download, "TCPConnector", connector_factory)
    monkeypatch.setattr(download, "ClientSession", Session)
    return responses, calls, session_arguments, connector_arguments


@pytest.mark.parametrize(
    "url",
    [
        "http://mosque.example.org/file.pdf",
        "https://mosque.example.org:444/file.pdf",
        "https://user:password@mosque.example.org/file.pdf",
        "https://@mosque.example.org/file.pdf",
        "https://mosque.example.org/file.pdf#page=1",
        "https://mosque.example.org/file.pdf#",
        "https://127.0.0.1/file.pdf",
        "https://127.9.8.7/file.pdf",
        "https://10.0.0.1/file.pdf",
        "https://172.16.1.1/file.pdf",
        "https://192.168.1.1/file.pdf",
        "https://169.254.169.254/file.pdf",
        "https://100.64.0.1/file.pdf",
        "https://192.0.2.1/file.pdf",
        "https://224.0.0.1/file.pdf",
        "https://0.0.0.0/file.pdf",
        "https://[::]/file.pdf",
        "https://[::1]/file.pdf",
        "https://[fc00::1]/file.pdf",
        "https://[fe80::1]/file.pdf",
        "https://[fec0::1]/file.pdf",
        "https://[ff02::1]/file.pdf",
        "https://[2001:db8::1]/file.pdf",
        "https://[::ffff:1.1.1.1]/file.pdf",
        "https://[64:ff9b::7f00:1]/file.pdf",
        "https://[2002:7f00:1::]/file.pdf",
        "https://[2001:0:4136:e378:8000:63bf:3fff:fdd2]/file.pdf",
        "https://[fe80::1%25eth0]/file.pdf",
        "https://localhost/file.pdf",
        "https://intranet/file.pdf",
        "https://mosque.local/file.pdf",
        "https://mosque.internal/file.pdf",
        "https://0x7f000001/file.pdf",
        "https://2130706433/file.pdf",
        "https://-bad.example.org/file.pdf",
        "https://bad_.example.org/file.pdf",
        "https://mosque.example.org\\@127.0.0.1/file.pdf",
        " https://mosque.example.org/file.pdf",
        "https://mosque.example.org/\nfile.pdf",
        "https://mosque.example.org/file.pdf\x00",
        "https://mosque.example.org/file.pdf?" + "a" * 2050,
        "",
        None,
    ],
)
def test_unsafe_url_rejected_without_dns(url):
    with pytest.raises(download.DownloadError) as error:
        download.validate_url(url)
    assert "password" not in str(error.value)
    assert "127.0.0.1" not in str(error.value)


@pytest.mark.parametrize(
    "url",
    [
        "https://mosque.example.org/file.pdf",
        "https://mosque.example.org:443/file.csv",
        "https://1.1.1.1/file.pdf",
        "https://[2606:4700:4700::1111]/file.pdf",
        "https://mosque.example.org./file.pdf",
    ],
)
def test_valid_public_syntax(url):
    assert download.validate_url(url).startswith("https://")


def answer(host="93.184.216.34", name="mosque.example.org"):
    return {
        "hostname": name,
        "host": host,
        "port": 443,
        "family": socket.AF_INET,
        "proto": 0,
        "flags": 0,
    }


async def test_connection_resolver_rejects_mixed_and_rebound_answers():
    delegate = AsyncMock()
    delegate.resolve.side_effect = [
        [answer()],
        [answer(), answer("127.0.0.1")],
        [answer("10.1.2.3")],
    ]
    resolver = download.PublicResolver(delegate)
    connector = download.TCPConnector(
        resolver=resolver, use_dns_cache=False, force_close=True
    )
    try:
        resolved = await connector._resolve_host("mosque.example.org", 443)
        assert resolved[0]["host"] == "93.184.216.34"
        for _ in range(2):
            with pytest.raises(download.DownloadError, match="public Internet"):
                await connector._resolve_host("mosque.example.org", 443)
        assert delegate.resolve.await_count == 3
    finally:
        await connector.close()
        await resolver.close()
    delegate.close.assert_awaited_once()


@pytest.mark.parametrize(
    "answers", [[], [answer("not-an-ip")], [answer("::ffff:127.0.0.1")]]
)
async def test_invalid_resolver_addresses_are_rejected(answers):
    delegate = AsyncMock()
    delegate.resolve.return_value = answers
    resolver = download.PublicResolver(delegate)
    with pytest.raises(download.DownloadError):
        await resolver.resolve("mosque.example.org", 443, socket.AF_UNSPEC)
    await resolver.close()


async def test_success_uses_verified_tls_no_proxy_or_cookies(transport):
    responses, calls, sessions, connectors = transport
    responses.append(
        Response(
            headers={
                "Content-Type": "application/pdf; charset=binary",
                "ETag": '"revision-1"',
                "Last-Modified": "Wed, 21 Oct 2026 00:00:00 GMT",
            }
        )
    )
    result = await download.async_download(PUBLIC_URL)
    assert result.content == PDF
    assert result.sha256 == sha256(PDF).hexdigest()
    assert result.media_type == "pdf"
    assert result.etag == '"revision-1"'
    assert not result.not_modified
    assert calls[0][1]["allow_redirects"] is False
    assert calls[0][1]["headers"]["Accept-Encoding"] == "identity"
    assert connectors[0]["ssl"] is True
    assert connectors[0]["use_dns_cache"] is False
    assert connectors[0]["force_close"] is True
    assert isinstance(connectors[0]["resolver"], download.PublicResolver)
    assert sessions[0]["trust_env"] is False
    assert sessions[0]["auto_decompress"] is False
    assert isinstance(sessions[0]["cookie_jar"], DummyCookieJar)
    assert sessions[0]["timeout"].connect == 10
    assert sessions[0]["timeout"].sock_read == 10
    assert sessions[0]["connector"].closed


@pytest.mark.parametrize(
    "content_type", ["text/csv", "application/csv", "text/plain; charset=utf-8"]
)
async def test_csv_success(transport, content_type):
    responses, *_ = transport
    responses.append(Response(body=CSV, headers={"Content-Type": content_type}))
    result = await download.async_download(
        "https://mosque.example.org/file.csv", media_type="csv"
    )
    assert result.content == CSV
    assert result.media_type == "csv"


async def test_relative_redirect_preserves_conditional_headers(transport):
    responses, calls, *_ = transport
    responses.extend(
        [
            Response(302, headers={"Location": "/updated.pdf"}),
            Response(304, headers={"ETag": '"same"'}),
        ]
    )
    result = await download.async_download(PUBLIC_URL, etag='"same"')
    assert result.content is None
    assert result.sha256 is None
    assert result.not_modified
    assert calls[1][0] == "https://mosque.example.org/updated.pdf"
    assert calls[1][1]["headers"]["If-None-Match"] == '"same"'


async def test_cross_origin_redirect_does_not_leak_validators(transport):
    responses, calls, *_ = transport
    responses.extend(
        [
            Response(302, headers={"Location": "https://cdn.example.org/source.pdf"}),
            Response(),
        ]
    )
    await download.async_download(
        PUBLIC_URL, etag='"private-id"', last_modified="Wed, 21 Oct 2026 00:00:00 GMT"
    )
    assert "If-None-Match" in calls[0][1]["headers"]
    assert "If-None-Match" not in calls[1][1]["headers"]
    assert "If-Modified-Since" not in calls[1][1]["headers"]


@pytest.mark.parametrize(
    "location",
    [
        "http://mosque.example.org/a.pdf",
        "https://127.0.0.1/a.pdf",
        "https://private.local/a.pdf",
        "https://user:secret@mosque.example.org/a.pdf",
        "https://@mosque.example.org/a.pdf",
        "//user:secret@mosque.example.org/a.pdf",
        "/a.pdf#page=2",
        "https://mosque.example.org:444/a.pdf",
    ],
)
async def test_unsafe_redirect_stops_before_next_request(transport, location):
    responses, calls, *_ = transport
    responses.append(Response(302, headers={"Location": location}))
    with pytest.raises(download.DownloadError) as error:
        await download.async_download(PUBLIC_URL)
    assert len(calls) == 1
    assert error.value.code == "unsafe_redirect"
    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    "location", [None, "", "/line\nbreak.pdf", "https://mosque.example.org\\a.pdf"]
)
async def test_invalid_redirect_location(transport, location):
    responses, *_ = transport
    responses.append(
        Response(302, headers={} if location is None else {"Location": location})
    )
    with pytest.raises(download.DownloadError) as error:
        await download.async_download(PUBLIC_URL)
    assert error.value.code == "invalid_redirect"


async def test_redirect_limit_is_bounded(transport):
    responses, calls, *_ = transport
    responses.extend(Response(302, headers={"Location": "/next.pdf"}) for _ in range(4))
    with pytest.raises(download.DownloadError) as error:
        await download.async_download(PUBLIC_URL)
    assert error.value.code == "too_many_redirects"
    assert len(calls) == 4


@pytest.mark.parametrize(
    "headers,expected",
    [
        ({"Content-Type": "text/html"}, "invalid_content_type"),
        ({"Content-Type": "application/octet-stream"}, "invalid_content_type"),
        ({}, "invalid_content_type"),
        (
            {"Content-Type": "application/pdf", "Content-Encoding": "gzip"},
            "unsupported_encoding",
        ),
        (
            {"Content-Type": "application/pdf", "Content-Encoding": "br"},
            "unsupported_encoding",
        ),
        (
            {
                "Content-Type": "application/pdf",
                "Content-Length": str(download.MAX_PDF_BYTES + 1),
            },
            "too_large",
        ),
        (
            {"Content-Type": "application/pdf", "Content-Length": "-1"},
            "invalid_content_length",
        ),
        (
            {"Content-Type": "application/pdf", "Content-Length": "abc"},
            "invalid_content_length",
        ),
        (
            {
                "Content-Type": "application/pdf",
                "Content-Length": "999999999999999999999",
            },
            "too_large",
        ),
    ],
)
async def test_response_headers_fail_before_reading(transport, headers, expected):
    responses, *_ = transport
    responses.append(
        Response(headers=headers, chunks=[AssertionError("must not read body")])
    )
    with pytest.raises(download.DownloadError) as error:
        await download.async_download(PUBLIC_URL)
    assert error.value.code == expected


@pytest.mark.parametrize(
    "kind,limit", [("pdf", download.MAX_PDF_BYTES), ("csv", download.MAX_CSV_BYTES)]
)
async def test_chunked_size_limit(transport, kind, limit):
    responses, *_ = transport
    responses.append(
        Response(
            headers={
                "Content-Type": "application/pdf" if kind == "pdf" else "text/csv"
            },
            chunks=[b"x" * limit, b"y"],
        )
    )
    with pytest.raises(download.DownloadError) as error:
        await download.async_download(PUBLIC_URL, media_type=kind)
    assert error.value.code == "too_large"


@pytest.mark.parametrize(
    "body", [b"", b"<!DOCTYPE html>failure", b"%PDF-1.7\ntruncated", b"%PDF-9.0\n%%EOF"]
)
async def test_pdf_content_signature(transport, body):
    responses, *_ = transport
    responses.append(Response(body=body))
    with pytest.raises(download.DownloadError) as error:
        await download.async_download(PUBLIC_URL)
    assert error.value.code == "invalid_content"


@pytest.mark.parametrize(
    "body",
    [
        b"",
        b"<!DOCTYPE html>failure",
        b"\xef\xbb\xbf<html>failure",
        b"\xffbinary",
        b"a,b\n\x00x,y",
        PDF,
    ],
)
async def test_csv_rejects_html_binary_and_pdf(transport, body):
    responses, *_ = transport
    responses.append(Response(body=body, headers={"Content-Type": "text/csv"}))
    with pytest.raises(download.DownloadError) as error:
        await download.async_download(PUBLIC_URL, media_type="csv")
    assert error.value.code == "invalid_content"


@pytest.mark.parametrize("status", [201, 204, 400, 403, 404, 500])
async def test_error_status_is_redacted(transport, status):
    responses, *_ = transport
    responses.append(Response(status))
    with pytest.raises(download.DownloadError) as error:
        await download.async_download(PUBLIC_URL)
    assert error.value.code == "http_error"
    assert str(status) in str(error.value)
    assert "private=value" not in str(error.value)


async def test_unrequested_304_rejected(transport):
    responses, *_ = transport
    responses.append(Response(304, headers={}))
    with pytest.raises(download.DownloadError) as error:
        await download.async_download(PUBLIC_URL)
    assert error.value.code == "unexpected_not_modified"


@pytest.mark.parametrize(
    "validator", ["x\r\nInjected: header", "x\x00", "x" * 513, "non-ASCII-£", ""]
)
async def test_invalid_outgoing_validator_never_sent(transport, validator):
    _, calls, *_ = transport
    with pytest.raises(download.DownloadError) as error:
        await download.async_download(PUBLIC_URL, etag=validator)
    assert error.value.code == "invalid_validator"
    assert not calls


async def test_invalid_response_validators_are_dropped(transport):
    responses, *_ = transport
    responses.append(
        Response(
            headers={
                "Content-Type": "application/pdf",
                "ETag": "x\r\nsecret",
                "Last-Modified": "x" * 513,
            }
        )
    )
    result = await download.async_download(PUBLIC_URL)
    assert result.etag is None
    assert result.last_modified is None


async def test_total_timeout_covers_streaming_and_closes_connector(
    monkeypatch, transport
):
    responses, _, sessions, _ = transport
    responses.append(Response(delay=1))
    monkeypatch.setattr(download, "TOTAL_TIMEOUT", 0.001)
    with pytest.raises(download.DownloadError) as error:
        await download.async_download(PUBLIC_URL)
    assert error.value.code == "timeout"
    assert sessions[0]["connector"].closed


async def test_transport_failure_does_not_expose_url(transport):
    responses, *_ = transport
    responses.append(ClientConnectionError(f"failed on {PUBLIC_URL}"))
    with pytest.raises(download.DownloadError) as error:
        await download.async_download(PUBLIC_URL)
    assert error.value.code == "connection_failed"
    assert "private=value" not in str(error.value)
    assert "mosque.example.org" not in str(error.value)


async def test_cancellation_propagates_and_closes_connector(transport):
    responses, _, sessions, _ = transport
    responses.append(Response(chunks=[asyncio.CancelledError()]))
    with pytest.raises(asyncio.CancelledError):
        await download.async_download(PUBLIC_URL)
    assert sessions[0]["connector"].closed


async def test_source_kind_is_explicit(transport):
    _, calls, *_ = transport
    with pytest.raises(download.DownloadError) as error:
        await download.async_download(PUBLIC_URL, media_type="html")
    assert error.value.code == "invalid_source_type"
    assert not calls
