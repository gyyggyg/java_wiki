"""生成 S1, S2, ... 短 id"""


class SectionIdGenerator:
    def __init__(self, prefix: str = "S", start: int = 1):
        self._counter = start
        self._prefix = prefix

    def next(self) -> str:
        s = f"{self._prefix}{self._counter}"
        self._counter += 1
        return s
