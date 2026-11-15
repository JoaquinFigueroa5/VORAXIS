"""An interrupted granule download resumes instead of starting over."""

from pathlib import Path

from app.integrations.nisar.earthdata_client import EarthdataClient


class FakeResponse:
    def __init__(self, chunks: list[bytes], status: int = 200, length: int | None = None):
        self.chunks = chunks
        self.status_code = status
        self.headers = {"Content-Length": str(length)} if length is not None else {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size: int):
        yield from self.chunks


class FakeSession:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.requests: list[dict] = []

    def get(self, _url: str, **kwargs):
        self.requests.append(kwargs)
        return self.response


def _client(session: FakeSession) -> EarthdataClient:
    client = EarthdataClient()
    client.session = lambda: session  # type: ignore[method-assign]
    return client


def test_a_partial_file_is_resumed_with_a_range_request(tmp_path: Path):
    destination = tmp_path / "granule.h5"
    (tmp_path / "granule.h5.part").write_bytes(b"abc")
    session = FakeSession(FakeResponse([b"def"], status=206, length=3))
    reported: list[tuple[int, int | None]] = []

    assert _client(session).download(
        "https://example.invalid/granule.h5", destination, progress=lambda d, t: reported.append((d, t))
    )
    assert destination.read_bytes() == b"abcdef"
    assert session.requests[0]["headers"] == {"Range": "bytes=3-"}
    assert reported[-1] == (6, 6)  # resumed bytes count towards the total


def test_a_server_without_range_support_starts_the_file_over(tmp_path: Path):
    destination = tmp_path / "granule.h5"
    (tmp_path / "granule.h5.part").write_bytes(b"abc")
    session = FakeSession(FakeResponse([b"xyz"], status=200, length=3))

    assert _client(session).download("https://example.invalid/granule.h5", destination)
    assert destination.read_bytes() == b"xyz"  # never a mixture of two responses


def test_a_failed_transfer_keeps_the_partial_file(tmp_path: Path):
    destination = tmp_path / "granule.h5"

    class Broken(FakeResponse):
        def iter_content(self, chunk_size: int):
            yield b"abc"
            raise ConnectionError("link dropped")

    try:
        _client(FakeSession(Broken([], length=6))).download("https://example.invalid/x.h5", destination)
    except ConnectionError:
        pass
    assert not destination.exists()
    assert (tmp_path / "granule.h5.part").read_bytes() == b"abc"  # the next run resumes here
