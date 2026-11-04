from __future__ import annotations

import ssl
import typing
from pathlib import Path

import httpcore
import pytest

import httpx
from httpx._transports.default import AsyncResponseStream, ResponseStream


class TrackedSyncStream:
    def __init__(self, items: list[bytes]) -> None:
        self.items = items
        self.closed = False

    def __iter__(self) -> typing.Iterator[bytes]:
        yield from self.items

    def close(self) -> None:
        self.closed = True


class TrackedAsyncStream:
    def __init__(self, items: list[bytes]) -> None:
        self.items = items
        self.closed = False

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        for item in self.items:
            yield item

    async def aclose(self) -> None:
        self.closed = True


class FaultySyncStream:
    def __init__(self, exc_to_raise: Exception) -> None:
        self.exc = exc_to_raise

    def __iter__(self) -> typing.Iterator[bytes]:
        yield b"initial_chunk"
        raise self.exc


class FaultyAsyncStream:
    def __init__(self, exc_to_raise: Exception) -> None:
        self.exc = exc_to_raise

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        yield b"initial_chunk"
        raise self.exc


def test_response_stream_close_lifecycle():
    stream = TrackedSyncStream([b"hello", b" ", b"world"])
    resp_stream = ResponseStream(stream)
    assert list(resp_stream) == [b"hello", b" ", b"world"]
    assert not stream.closed
    resp_stream.close()
    assert stream.closed


def test_response_stream_close_without_close_method():
    raw_stream = [b"chunk1", b"chunk2"]
    resp_stream = ResponseStream(raw_stream)
    assert list(resp_stream) == [b"chunk1", b"chunk2"]
    resp_stream.close()


@pytest.mark.parametrize(
    "httpcore_exc, expected_httpx_exc",
    [
        (httpcore.ReadTimeout("Timed out reading"), httpx.ReadTimeout),
        (httpcore.ReadError("Socket read failure"), httpx.ReadError),
        (httpcore.RemoteProtocolError("Peer disconnected"), httpx.RemoteProtocolError),
    ],
)
def test_response_stream_exception_mapping(
    httpcore_exc: Exception, expected_httpx_exc: type[httpx.HTTPError]
):
    stream = FaultySyncStream(httpcore_exc)
    resp_stream = ResponseStream(stream)
    with pytest.raises(expected_httpx_exc):
        list(resp_stream)


@pytest.mark.anyio
async def test_async_response_stream_aclose_lifecycle():
    stream = TrackedAsyncStream([b"async", b" ", b"stream"])
    resp_stream = AsyncResponseStream(stream)
    assert [part async for part in resp_stream] == [b"async", b" ", b"stream"]
    assert not stream.closed
    await resp_stream.aclose()
    assert stream.closed


@pytest.mark.anyio
async def test_async_response_stream_aclose_without_aclose_method():
    async def async_generator():
        yield b"chunk"

    resp_stream = AsyncResponseStream(async_generator())
    assert [part async for part in resp_stream] == [b"chunk"]
    await resp_stream.aclose()


@pytest.mark.anyio
@pytest.mark.parametrize(
    "httpcore_exc, expected_httpx_exc",
    [
        (httpcore.ReadTimeout("Async timeout reading"), httpx.ReadTimeout),
        (httpcore.ReadError("Async socket error"), httpx.ReadError),
        (
            httpcore.RemoteProtocolError("Async peer disconnected"),
            httpx.RemoteProtocolError,
        ),
    ],
)
async def test_async_response_stream_exception_mapping(
    httpcore_exc: Exception, expected_httpx_exc: type[httpx.HTTPError]
):
    stream = FaultyAsyncStream(httpcore_exc)
    resp_stream = AsyncResponseStream(stream)
    with pytest.raises(expected_httpx_exc):
        _ = [part async for part in resp_stream]


def test_http_transport_context_manager():
    with httpx.HTTPTransport() as transport:
        assert isinstance(transport, httpx.HTTPTransport)
        assert transport._pool is not None


@pytest.mark.anyio
async def test_async_http_transport_context_manager():
    async with httpx.AsyncHTTPTransport() as transport:
        assert isinstance(transport, httpx.AsyncHTTPTransport)
        assert transport._pool is not None


def test_http_transport_defaults():
    transport = httpx.HTTPTransport()
    assert transport._pool._http1 is True
    assert transport._pool._http2 is False
    assert transport._pool._ssl_context.verify_mode == ssl.CERT_REQUIRED


@pytest.mark.anyio
async def test_async_http_transport_defaults():
    transport = httpx.AsyncHTTPTransport()
    assert transport._pool._http1 is True
    assert transport._pool._http2 is False
    assert transport._pool._ssl_context.verify_mode == ssl.CERT_REQUIRED


def test_http_transport_trust_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    invalid_cert = tmp_path / "invalid_ca.pem"
    invalid_cert.write_text("INVALID_CERT_DATA", encoding="utf-8")
    monkeypatch.setenv("SSL_CERT_FILE", str(invalid_cert))

    with pytest.raises(ssl.SSLError):
        httpx.HTTPTransport()

    transport = httpx.HTTPTransport(trust_env=False)
    assert transport._pool is not None


@pytest.mark.anyio
async def test_async_http_transport_trust_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    invalid_cert = tmp_path / "invalid_ca.pem"
    invalid_cert.write_text("INVALID_CERT_DATA", encoding="utf-8")
    monkeypatch.setenv("SSL_CERT_FILE", str(invalid_cert))

    with pytest.raises(ssl.SSLError):
        httpx.AsyncHTTPTransport()

    transport = httpx.AsyncHTTPTransport(trust_env=False)
    assert transport._pool is not None


def test_http_transport_proxy_routing():
    direct = httpx.HTTPTransport()
    assert isinstance(direct._pool, httpcore.ConnectionPool)

    http_proxy = httpx.HTTPTransport(proxy="http://127.0.0.1:8080")
    assert isinstance(http_proxy._pool, httpcore.HTTPProxy)

    socks_proxy = httpx.HTTPTransport(proxy="socks5://127.0.0.1:1080")
    assert isinstance(socks_proxy._pool, httpcore.SOCKSProxy)


@pytest.mark.anyio
async def test_async_http_transport_proxy_routing():
    direct = httpx.AsyncHTTPTransport()
    assert isinstance(direct._pool, httpcore.AsyncConnectionPool)

    http_proxy = httpx.AsyncHTTPTransport(proxy="http://127.0.0.1:8080")
    assert isinstance(http_proxy._pool, httpcore.AsyncHTTPProxy)

    socks_proxy = httpx.AsyncHTTPTransport(proxy="socks5://127.0.0.1:1080")
    assert isinstance(socks_proxy._pool, httpcore.AsyncSOCKSProxy)


def test_http_transport_invalid_proxy_scheme():
    with pytest.raises(ValueError, match="Unknown scheme for proxy URL"):
        httpx.HTTPTransport(proxy="ftp://127.0.0.1")


@pytest.mark.anyio
async def test_async_http_transport_invalid_proxy_scheme():
    with pytest.raises(ValueError, match="Unknown scheme for proxy URL"):
        httpx.AsyncHTTPTransport(proxy="ftp://127.0.0.1")
