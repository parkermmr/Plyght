import json
import logging
import traceback
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Callable, Mapping


class JsonFormatter(logging.Formatter):
    """
    Schema-driven JSON formatter.

    :param schema: Mapping that describes the output structure.  If *None*, a default
                   schema of ``time``, ``level``, ``msg`` and ``@all`` is used.
    :param indent: Indentation passed straight to `json.dumps`.
    :param sort_keys: Whether `json.dumps` should sort keys alphabetically.

    Schema Values
    -------------
    *Special tokens* (strings starting with ``@``):

    ================ ==========================================================
    Token            Meaning
    ================ ==========================================================
    ``@time``       | ISO-8601 UTC timestamp with "Z" suffix.
    ``@level``      | ``record.levelname``.
    ``@message ``   | ``record.getMessage()`` (after %-style expansion).
    ``@exception `` | Traceback string if ``exc_info`` is present, else *None*.
    ``@logger``     | ``record.name``.
    ``@module``     | ``record.module``.
    ``@file``       | ``record.pathname``.
    ``@line``       | ``record.lineno``.
    ``@all``        | Splice point for unmapped attributes. **Key only**; the
                    |  corresponding value is ignored.
    ================ ==========================================================

    Any other string is treated as an attribute name on the record. Callables
    are invoked with the record and their return value is inserted verbatim.
    """

    _SPECIAL: Mapping[str, Callable[[logging.LogRecord], Any]] = MappingProxyType(
        {
            "@time": lambda r: datetime.fromtimestamp(
                r.created, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "@level": lambda r: r.levelname,
            "@message": lambda r: r.getMessage(),
            "@exception": lambda r: "".join(traceback.format_exception(*r.exc_info))
            if r.exc_info
            else None,
            "@logger": lambda r: r.name,
            "@module": lambda r: r.module,
            "@file": lambda r: r.pathname,
            "@line": lambda r: r.lineno,
        }
    )

    def __init__(
        self,
        schema: Mapping[str, Any] | None = None,
        *,
        indent: int | None = None,
        sort_keys: bool = False,
    ):
        """
        Create a new formatter.

        :param schema: Mapping defining the log layout; see *class* docstring.
        :param indent: Number of spaces for pretty-printing JSON. ``None`` ⇒ minified.
        :param sort_keys: Forwarded to :pyfunc:`json.dumps`.
        """
        super().__init__()
        self.schema = dict(
            schema
            or {
                "time": "@time",
                "level": "@level",
                "msg": "@message",
                "@all": None,
            }
        )
        self.indent = indent
        self.sort_keys = sort_keys

    @staticmethod
    def _json_safe(val: Any) -> Any:
        """
        Ensure *val* is JSON-serialisable.

        Returns *val* unchanged if ``json.dumps`` succeeds, otherwise the
        value's string representation.
        """
        try:
            json.dumps(val)
            return val
        except TypeError:
            return str(val)

    def _resolve(self, spec: Any, rec: logging.LogRecord) -> Any:
        """
        Resolve a *schema specifier* against *rec*.

        * If *spec* is callable -> return ``spec(rec)``.
        * If *spec* is a special token -> return its handler result.
        * Otherwise treat *spec* as a record attribute name.
        """
        if callable(spec):
            return spec(rec)
        if isinstance(spec, str) and spec in self._SPECIAL:
            return self._SPECIAL[spec](rec)
        return getattr(rec, spec, None)

    def _extras(self, rec: logging.LogRecord, consumed: set[str]) -> dict[str, Any]:
        """
        Collect unmapped attributes for the ``@all`` splice-point.

        :param rec: Source `~logging.LogRecord`.
        :param consumed: Keys already present in the payload.

        :return dict: JSON-safe mapping of remaining attributes (``None`` values and
                      private names are skipped).
        """
        out: dict[str, Any] = {}
        for k, v in rec.__dict__.items():
            if (
                k not in consumed
                and not k.startswith("_")
                and v is not None
            ):
                out[k] = self._json_safe(v)
        return out

    def format(self, rec: logging.LogRecord) -> str:
        """
        Serialise *rec* to a JSON string according to the schema.

        The algorithm walks the schema in order, populating the output dict.
        When the key ``"@all"`` is encountered (or after traversal if absent)
        every remaining attribute is spliced in exactly once.
        """
        payload: dict[str, Any] = {}
        consumed: set[str] = set()

        for key, spec in self.schema.items():
            if key == "@all":
                payload.update(self._extras(rec, consumed))
                continue
            if (val := self._resolve(spec, rec)) is not None:
                payload[key] = val
                consumed.add(key)

        if "@all" not in self.schema:
            payload.update(self._extras(rec, consumed))

        return json.dumps(payload, indent=self.indent, sort_keys=self.sort_keys)
