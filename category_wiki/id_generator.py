"""生成 S1, S2, ... 这种短 id（对齐总揽.json 的 S80/S1/S2 格式）"""


class SectionIdGenerator:
    def __init__(self, prefix: str = "S", start: int = 1):
        self._counter = start
        self._prefix = prefix

    def next(self) -> str:
        s = f"{self._prefix}{self._counter}"
        self._counter += 1
        return s
