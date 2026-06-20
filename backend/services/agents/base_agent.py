"""Base class every agent inherits from."""


class BaseAgent:
    label: str = ""
    system: str = ""
    keywords: list[str] = []

    @classmethod
    def to_dict(cls) -> dict:
        return {
            "label": cls.label,
            "system": cls.system,
            "keywords": cls.keywords,
        }