from __future__ import annotations

from streamlink.exceptions import StreamError
from streamlink.session import Streamlink
from streamlink.stream.stream import Stream
from streamlink.stream.wrappers import StreamIOIterWrapper, StreamIOThreadWrapper


class HTTPStream(Stream):
    """
    An HTTP stream using the :mod:`requests` library.
    """

    __shortname__ = "http"

    args: dict
    """A dict of keyword arguments passed to :meth:`requests.Session.request`, such as method, headers, cookies, etc."""

    def __init__(
        self,
        session: Streamlink,
        url: str,
        buffered: bool = True,
        **kwargs,
    ):
        """
        :param session: Streamlink session instance
        :param url: The URL of the HTTP stream
        :param buffered: Wrap stream output in an additional reader-thread
        :param kwargs: Additional keyword arguments passed to :meth:`requests.Session.request`
        """

        super().__init__(session)
        self.args = self.session.http.valid_request_args(**kwargs)
        self.args["url"] = url
        self.buffered = buffered
        self.fd = None
        self.res = None
        self.chunk_size = self.session.get_option("chunk-size")

    def __json__(self):  # noqa: PLW3201
        req = self.session.http.prepare_new_request(**self.args)

        return dict(
            type=self.shortname(),
            method=req.method,
            url=req.url,
            headers=dict(req.headers),
            body=req.body,
        )

    def to_url(self):
        return self.url

    @property
    def url(self) -> str:
        """
        The URL to the stream, prepared by :mod:`requests` with parameters read from :attr:`args`.
        """

        return self.session.http.prepare_new_request(**self.args).url  # type: ignore[return-value]

    def open(self):
        timeout_job = self.session.options.get("stream-timeout")
        timeout_con = self.session.options.get("http-timeout") or (10,20)
        reqargs = self.session.http.valid_request_args(**self.args)
        reqargs.setdefault("method", "GET")

        self.res = self.session.http.request(
            stream=True,
            exception=StreamError,
            timeout=timeout_con,
            **reqargs,
        )

        self.fd = StreamIOIterWrapper(self.res.iter_content(self.chunk_size))
        if self.buffered:
            self.fd = StreamIOThreadWrapper(self.session, self.fd, timeout=timeout_job, chunk_size=self.chunk_size)

        return self.fd

    def close(self):
        if hasattr(self.res, "close"):
            try: self.res.close()
            except: pass
        if hasattr(self.fd, "close"):
            try: self.fd.close()
            except: pass

