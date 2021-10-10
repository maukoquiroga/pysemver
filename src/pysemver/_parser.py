from __future__ import annotations

import textwrap
from typing import Any, Generator, Sequence, Set, Tuple

from ._builder import Contract, ContractBuilder
from ._repo import Repo
from ._types import What

THIS: str = Repo.Version.this()
THAT: str = Repo.Version.last()


class Parser:
    """Wrapper around the repo and the contract builder.

    Attributes:
        repo: To query files and changes from.
        this: The base revision.
        that: The revision to compare with.
        diff: The list of files changed between ``this`` and ``that``.
        current: ``this`` or ``that``.
        builder: A contract builder.
        contracts: The list of built contracts.

    Args:
        repo: The repo to use, defaults to :class:`.Repo`.
        this: The revision to use, defaults to ``HEAD``.
        that: The revision to compare ``this`` with, defaults to last version.

    Examples:
        >>> parser = Parser(this = "0.4.0", that = "0.2.0")

        >>> parser.diff
        ['.gitignore', '.python-version', 'Makefile', 'noxfile.py', 'poetry...

        >>> with parser(what = "this") as parsing:
        ...     list(parsing)
        ...
        [(1, 7), (2, 7), (3, 7), (4, 7), (5, 7), (6, 7), (7, 7)]

        >>> this = set(parser.contracts)

        >>> with parser(what = "that") as parsing:
        ...     list(parsing)
        ...
        [(1, 6), (2, 6), (3, 6), (4, 6), (5, 6), (6, 6)]

        >>> that = set(parser.contracts)

        >>> with parser(what = "thus") as parsing:
        ...     print("wut!")
        ...
        Traceback (most recent call last):
        AttributeError: 'Parser' object has no attribute 'thus'

        >>> next(iter(this ^ that & this))  # Added functions…
        Contract(name='...', ...

        >>> next(iter(that ^ this & that))  # Removed functions…
        Contract(name='...', ...

    .. versionadded:: 36.1.0

    """

    this: str
    that: str
    diff: Sequence[str]
    current: str
    builder: ContractBuilder
    contracts: Sequence[Contract]

    def __init__(self, *, this: str = THIS, that: str = THAT) -> None:
        self.this = this
        self.that = that
        self.diff = Repo.File.diff(this, that)

    def __call__(self, *, what: What) -> Parser:
        # We try recover the revision (``this`` or ``that``). Fails otherwise.
        self.current: str = self.__getattribute__(what)

        # And we return ourselves.
        return self

    def __enter__(self) -> Generator[Tuple[int, ...], None, None]:
        # We recover the python files corresponding to ``revison``.
        files: Set[str] = {
            file
            for file in Repo.File.tree(self.current)
            if file.endswith(".py")
            }

        # We only keep the files changed between ``this`` and ``that``.
        to_parse: Set[str] = files & set(self.diff)

        # We create a builder with the selected files.
        self.builder: ContractBuilder = ContractBuilder(tuple(to_parse))

        # And finally we iterate over the files…
        for file in self.builder.files:

            # We recover the contents of ``file`` at ``revision``.
            content: str = Repo.File.show(self.current, file)

            # We sanitize the source code.
            source: str = textwrap.dedent(content)

            # Then pass it on to the contract builder.
            self.builder(source)

            # And we yield a counter to keep the user updated.
            yield self.builder.count, self.builder.total

    def __exit__(self, *__: Any) -> None:
        # We save the contracts for upstream recovery.
        self.contracts = self.builder.contracts
