import io
import typing

import pytest

import httpx

method = "POST"
url = "https://www.example.com"


@pytest.mark.anyio
async def test_empty_content():
    request = httpx.Request(method, url)
    assert isinstance(request.stream, httpx.SyncByteStream)
    assert isinstance(request.stream, httpx.AsyncByteStream)

    sync_content = b"".join(list(request.stream))
    async_content = b"".join([part async for part in request.stream])

    assert request.headers == {"Host": "www.example.com", "Content-Length": "0"}
    assert sync_content == b""
    assert async_content == b""


@pytest.mark.anyio
async def test_bytes_content():
    request = httpx.Request(method, url, content=b"Hello, world!")
    assert isinstance(request.stream, typing.Iterable)
    assert isinstance(request.stream, typing.AsyncIterable)

    sync_content = b"".join(list(request.stream))
    async_content = b"".join([part async for part in request.stream])

    assert request.headers == {"Host": "www.example.com", "Content-Length": "13"}
    assert sync_content == b"Hello, world!"
    assert async_content == b"Hello, world!"

    # Support 'data' for compat with requests.
    with pytest.warns(DeprecationWarning):
        request = httpx.Request(method, url, data=b"Hello, world!")  # type: ignore
    assert isinstance(request.stream, typing.Iterable)
    assert isinstance(request.stream, typing.AsyncIterable)

    sync_content = b"".join(list(request.stream))
    async_content = b"".join([part async for part in request.stream])

    assert request.headers == {"Host": "www.example.com", "Content-Length": "13"}
    assert sync_content == b"Hello, world!"
    assert async_content == b"Hello, world!"


@pytest.mark.anyio
async def test_bytesio_content():
    request = httpx.Request(method, url, content=io.BytesIO(b"Hello, world!"))
    assert isinstance(request.stream, typing.Iterable)
    assert not isinstance(request.stream, typing.AsyncIterable)

    content = b"".join(list(request.stream))

    assert request.headers == {"Host": "www.example.com", "Content-Length": "13"}
    assert content == b"Hello, world!"


@pytest.mark.anyio
async def test_async_bytesio_content():
    class AsyncBytesIO:
        def __init__(self, content: bytes) -> None:
            self._idx = 0
            self._content = content

        async def aread(self, chunk_size: int) -> bytes:
            chunk = self._content[self._idx : self._idx + chunk_size]
            self._idx = self._idx + chunk_size
            return chunk

        async def __aiter__(self):
            yield self._content  # pragma: no cover

    request = httpx.Request(method, url, content=AsyncBytesIO(b"Hello, world!"))
    assert not isinstance(request.stream, typing.Iterable)
    assert isinstance(request.stream, typing.AsyncIterable)

    content = b"".join([part async for part in request.stream])

    assert request.headers == {
        "Host": "www.example.com",
        "Transfer-Encoding": "chunked",
    }
    assert content == b"Hello, world!"


@pytest.mark.anyio
async def test_iterator_content():
    def hello_world() -> typing.Iterator[bytes]:
        yield b"Hello, "
        yield b"world!"

    request = httpx.Request(method, url, content=hello_world())
    assert isinstance(request.stream, typing.Iterable)
    assert not isinstance(request.stream, typing.AsyncIterable)

    content = b"".join(list(request.stream))

    assert request.headers == {
        "Host": "www.example.com",
        "Transfer-Encoding": "chunked",
    }
    assert content == b"Hello, world!"

    with pytest.raises(httpx.StreamConsumed):
        list(request.stream)

    # Support 'data' for compat with requests.
    with pytest.warns(DeprecationWarning):
        request = httpx.Request(method, url, data=hello_world())  # type: ignore
    assert isinstance(request.stream, typing.Iterable)
    assert not isinstance(request.stream, typing.AsyncIterable)

    content = b"".join(list(request.stream))

    assert request.headers == {
        "Host": "www.example.com",
        "Transfer-Encoding": "chunked",
    }
    assert content == b"Hello, world!"


@pytest.mark.anyio
async def test_aiterator_content():
    async def hello_world() -> typing.AsyncIterator[bytes]:
        yield b"Hello, "
        yield b"world!"

    request = httpx.Request(method, url, content=hello_world())
    assert not isinstance(request.stream, typing.Iterable)
    assert isinstance(request.stream, typing.AsyncIterable)

    content = b"".join([part async for part in request.stream])

    assert request.headers == {
        "Host": "www.example.com",
        "Transfer-Encoding": "chunked",
    }
    assert content == b"Hello, world!"

    with pytest.raises(httpx.StreamConsumed):
        [part async for part in request.stream]

    # Support 'data' for compat with requests.
    with pytest.warns(DeprecationWarning):
        request = httpx.Request(method, url, data=hello_world())  # type: ignore
    assert not isinstance(request.stream, typing.Iterable)
    assert isinstance(request.stream, typing.AsyncIterable)

    content = b"".join([part async for part in request.stream])

    assert request.headers == {
        "Host": "www.example.com",
        "Transfer-Encoding": "chunked",
    }
    assert content == b"Hello, world!"


@pytest.mark.anyio
async def test_json_content():
    request = httpx.Request(method, url, json={"Hello": "world!"})
    assert isinstance(request.stream, typing.Iterable)
    assert isinstance(request.stream, typing.AsyncIterable)

    sync_content = b"".join(list(request.stream))
    async_content = b"".join([part async for part in request.stream])

    assert request.headers == {
        "Host": "www.example.com",
        "Content-Length": "18",
        "Content-Type": "application/json",
    }
    assert sync_content == b'{"Hello":"world!"}'
    assert async_content == b'{"Hello":"world!"}'


@pytest.mark.anyio
async def test_urlencoded_content():
    request = httpx.Request(method, url, data={"Hello": "world!"})
    assert isinstance(request.stream, typing.Iterable)
    assert isinstance(request.stream, typing.AsyncIterable)

    sync_content = b"".join(list(request.stream))
    async_content = b"".join([part async for part in request.stream])

    assert request.headers == {
        "Host": "www.example.com",
        "Content-Length": "14",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    assert sync_content == b"Hello=world%21"
    assert async_content == b"Hello=world%21"


@pytest.mark.anyio
async def test_urlencoded_boolean():
    request = httpx.Request(method, url, data={"example": True})
    assert isinstance(request.stream, typing.Iterable)
    assert isinstance(request.stream, typing.AsyncIterable)

    sync_content = b"".join(list(request.stream))
    async_content = b"".join([part async for part in request.stream])

    assert request.headers == {
        "Host": "www.example.com",
        "Content-Length": "12",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    assert sync_content == b"example=true"
    assert async_content == b"example=true"


@pytest.mark.anyio
async def test_urlencoded_none():
    request = httpx.Request(method, url, data={"example": None})
    assert isinstance(request.stream, typing.Iterable)
    assert isinstance(request.stream, typing.AsyncIterable)

    sync_content = b"".join(list(request.stream))
    async_content = b"".join([part async for part in request.stream])

    assert request.headers == {
        "Host": "www.example.com",
        "Content-Length": "8",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    assert sync_content == b"example="
    assert async_content == b"example="


@pytest.mark.anyio
async def test_urlencoded_list():
    request = httpx.Request(method, url, data={"example": ["a", 1, True]})
    assert isinstance(request.stream, typing.Iterable)
    assert isinstance(request.stream, typing.AsyncIterable)

    sync_content = b"".join(list(request.stream))
    async_content = b"".join([part async for part in request.stream])

    assert request.headers == {
        "Host": "www.example.com",
        "Content-Length": "32",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    assert sync_content == b"example=a&example=1&example=true"
    assert async_content == b"example=a&example=1&example=true"


@pytest.mark.anyio
async def test_multipart_files_content():
    files = {"file": io.BytesIO(b"<file content>")}
    headers = {"Content-Type": "multipart/form-data; boundary=+++"}
    request = httpx.Request(
        method,
        url,
        files=files,
        headers=headers,
    )
    assert isinstance(request.stream, typing.Iterable)
    assert isinstance(request.stream, typing.AsyncIterable)

    sync_content = b"".join(list(request.stream))
    async_content = b"".join([part async for part in request.stream])

    assert request.headers == {
        "Host": "www.example.com",
        "Content-Length": "138",
        "Content-Type": "multipart/form-data; boundary=+++",
    }
    assert sync_content == b"".join(
        [
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content>\r\n",
            b"--+++--\r\n",
        ]
    )
    assert async_content == b"".join(
        [
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content>\r\n",
            b"--+++--\r\n",
        ]
    )


@pytest.mark.anyio
async def test_multipart_data_and_files_content():
    data = {"message": "Hello, world!"}
    files = {"file": io.BytesIO(b"<file content>")}
    headers = {"Content-Type": "multipart/form-data; boundary=+++"}
    request = httpx.Request(method, url, data=data, files=files, headers=headers)
    assert isinstance(request.stream, typing.Iterable)
    assert isinstance(request.stream, typing.AsyncIterable)

    sync_content = b"".join(list(request.stream))
    async_content = b"".join([part async for part in request.stream])

    assert request.headers == {
        "Host": "www.example.com",
        "Content-Length": "210",
        "Content-Type": "multipart/form-data; boundary=+++",
    }
    assert sync_content == b"".join(
        [
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="message"\r\n',
            b"\r\n",
            b"Hello, world!\r\n",
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content>\r\n",
            b"--+++--\r\n",
        ]
    )
    assert async_content == b"".join(
        [
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="message"\r\n',
            b"\r\n",
            b"Hello, world!\r\n",
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content>\r\n",
            b"--+++--\r\n",
        ]
    )


@pytest.mark.anyio
async def test_empty_request():
    request = httpx.Request(method, url, data={}, files={})
    assert isinstance(request.stream, typing.Iterable)
    assert isinstance(request.stream, typing.AsyncIterable)

    sync_content = b"".join(list(request.stream))
    async_content = b"".join([part async for part in request.stream])

    assert request.headers == {"Host": "www.example.com", "Content-Length": "0"}
    assert sync_content == b""
    assert async_content == b""


def test_invalid_argument():
    with pytest.raises(TypeError):
        httpx.Request(method, url, content=123)  # type: ignore

    with pytest.raises(TypeError):
        httpx.Request(method, url, content={"a": "b"})  # type: ignore


@pytest.mark.anyio
async def test_multipart_multiple_files_single_input_content():
    files = [
        ("file", io.BytesIO(b"<file content 1>")),
        ("file", io.BytesIO(b"<file content 2>")),
    ]
    headers = {"Content-Type": "multipart/form-data; boundary=+++"}
    request = httpx.Request(method, url, files=files, headers=headers)
    assert isinstance(request.stream, typing.Iterable)
    assert isinstance(request.stream, typing.AsyncIterable)

    sync_content = b"".join(list(request.stream))
    async_content = b"".join([part async for part in request.stream])

    assert request.headers == {
        "Host": "www.example.com",
        "Content-Length": "271",
        "Content-Type": "multipart/form-data; boundary=+++",
    }
    assert sync_content == b"".join(
        [
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content 1>\r\n",
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content 2>\r\n",
            b"--+++--\r\n",
        ]
    )
    assert async_content == b"".join(
        [
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content 1>\r\n",
            b"--+++\r\n",
            b'Content-Disposition: form-data; name="file"; filename="upload"\r\n',
            b"Content-Type: application/octet-stream\r\n",
            b"\r\n",
            b"<file content 2>\r\n",
            b"--+++--\r\n",
        ]
    )


@pytest.mark.anyio
async def test_response_empty_content():
    response = httpx.Response(200)
    assert isinstance(response.stream, typing.Iterable)
    assert isinstance(response.stream, typing.AsyncIterable)

    sync_content = b"".join(list(response.stream))
    async_content = b"".join([part async for part in response.stream])

    assert response.headers == {}
    assert sync_content == b""
    assert async_content == b""


@pytest.mark.anyio
async def test_response_bytes_content():
    response = httpx.Response(200, content=b"Hello, world!")
    assert isinstance(response.stream, typing.Iterable)
    assert isinstance(response.stream, typing.AsyncIterable)

    sync_content = b"".join(list(response.stream))
    async_content = b"".join([part async for part in response.stream])

    assert response.headers == {"Content-Length": "13"}
    assert sync_content == b"Hello, world!"
    assert async_content == b"Hello, world!"


@pytest.mark.anyio
async def test_response_iterator_content():
    def hello_world() -> typing.Iterator[bytes]:
        yield b"Hello, "
        yield b"world!"

    response = httpx.Response(200, content=hello_world())
    assert isinstance(response.stream, typing.Iterable)
    assert not isinstance(response.stream, typing.AsyncIterable)

    content = b"".join(list(response.stream))

    assert response.headers == {"Transfer-Encoding": "chunked"}
    assert content == b"Hello, world!"

    with pytest.raises(httpx.StreamConsumed):
        list(response.stream)


@pytest.mark.anyio
async def test_response_aiterator_content():
    async def hello_world() -> typing.AsyncIterator[bytes]:
        yield b"Hello, "
        yield b"world!"

    response = httpx.Response(200, content=hello_world())
    assert not isinstance(response.stream, typing.Iterable)
    assert isinstance(response.stream, typing.AsyncIterable)

    content = b"".join([part async for part in response.stream])

    assert response.headers == {"Transfer-Encoding": "chunked"}
    assert content == b"Hello, world!"

    with pytest.raises(httpx.StreamConsumed):
        [part async for part in response.stream]


def test_response_invalid_argument():
    with pytest.raises(TypeError):
        httpx.Response(200, content=123)  # type: ignore


def test_ensure_ascii_false_with_french_characters():
    data = {"greeting": "Bonjour, ça va ?"}
    response = httpx.Response(200, json=data)
    assert "ça va" in response.text, (
        "ensure_ascii=False should preserve French accented characters"
    )
    assert response.headers["Content-Type"] == "application/json"


def test_separators_for_compact_json():
    data = {"clé": "valeur", "liste": [1, 2, 3]}
    response = httpx.Response(200, json=data)
    assert response.text == '{"clé":"valeur","liste":[1,2,3]}', (
        "separators=(',', ':') should produce a compact representation"
    )
    assert response.headers["Content-Type"] == "application/json"


def test_allow_nan_false():
    data_with_nan = {"nombre": float("nan")}
    data_with_inf = {"nombre": float("inf")}

    with pytest.raises(
        ValueError, match="Out of range float values are not JSON compliant"
    ):
        httpx.Response(200, json=data_with_nan)
    with pytest.raises(
        ValueError, match="Out of range float values are not JSON compliant"
    ):
        httpx.Response(200, json=data_with_inf)


@pytest.mark.anyio
async def test_response_text_content():
    response = httpx.Response(200, text="Hello, world!")
    assert isinstance(response.stream, typing.Iterable)
    assert isinstance(response.stream, typing.AsyncIterable)

    sync_content = b"".join(list(response.stream))
    async_content = b"".join([part async for part in response.stream])

    assert response.headers == {
        "Content-Length": "13",
        "Content-Type": "text/plain; charset=utf-8",
    }
    assert sync_content == b"Hello, world!"
    assert async_content == b"Hello, world!"


@pytest.mark.anyio
async def test_response_html_content():
    response = httpx.Response(200, html="<h1>Hello, world!</h1>")
    assert isinstance(response.stream, typing.Iterable)
    assert isinstance(response.stream, typing.AsyncIterable)

    sync_content = b"".join(list(response.stream))
    async_content = b"".join([part async for part in response.stream])

    assert response.headers == {
        "Content-Length": "22",
        "Content-Type": "text/html; charset=utf-8",
    }
    assert sync_content == b"<h1>Hello, world!</h1>"
    assert async_content == b"<h1>Hello, world!</h1>"


@pytest.mark.anyio
async def test_response_empty_text():
    response = httpx.Response(200, text="")
    assert response.headers == {
        "Content-Length": "0",
        "Content-Type": "text/plain; charset=utf-8",
    }
    assert response.content == b""


@pytest.mark.anyio
async def test_response_empty_html():
    response = httpx.Response(200, html="")
    assert response.headers == {
        "Content-Length": "0",
        "Content-Type": "text/html; charset=utf-8",
    }
    assert response.content == b""


def test_content_dict_rejected():
    with pytest.raises(TypeError, match="Unexpected type for 'content'"):
        httpx.Request("POST", "https://example.com", content={"key": "val"})  # type: ignore


def test_unattached_stream():
    from httpx._content import UnattachedStream

    stream = UnattachedStream()
    with pytest.raises(httpx.StreamClosed):
        list(stream)


@pytest.mark.anyio
async def test_async_unattached_stream():
    from httpx._content import UnattachedStream

    stream = UnattachedStream()
    with pytest.raises(httpx.StreamClosed):
        _ = [part async for part in stream]


@pytest.mark.anyio
async def test_filelike_large_content():
    large_payload = b"X" * 150_000
    filelike = io.BytesIO(large_payload)
    request = httpx.Request("POST", "https://example.com", content=filelike)
    assert request.headers["Content-Length"] == "150000"

    chunks = list(request.stream)
    assert len(chunks) == 3
    assert len(chunks[0]) == 65_536
    assert len(chunks[1]) == 65_536
    assert len(chunks[2]) == 150_000 - (65_536 * 2)
    assert b"".join(chunks) == large_payload


@pytest.mark.anyio
async def test_async_filelike_large_content():
    class AsyncLargeFile:
        def __init__(self, data: bytes) -> None:
            self._idx = 0
            self._data = data

        async def aread(self, chunk_size: int) -> bytes:
            chunk = self._data[self._idx : self._idx + chunk_size]
            self._idx += chunk_size
            return chunk

        async def __aiter__(self):
            yield self._data  # pragma: no cover

    large_payload = b"Y" * 150_000
    filelike = AsyncLargeFile(large_payload)
    request = httpx.Request("POST", "https://example.com", content=filelike)  # type: ignore
    assert request.headers["Transfer-Encoding"] == "chunked"

    chunks = [part async for part in request.stream]
    assert len(chunks) == 3
    assert len(chunks[0]) == 65_536
    assert len(chunks[1]) == 65_536
    assert len(chunks[2]) == 150_000 - (65_536 * 2)
    assert b"".join(chunks) == large_payload
