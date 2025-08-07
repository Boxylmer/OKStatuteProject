

class StatuteReference:
    def __init__(self, title: str, section: str, version: str | None = None, subsection: str | None = None):
        self.title = title
        self.section = section
        self.version = version
        self.subsection = subsection

    def key(self) -> str:
        version = self.version or ""
        return f"{self.title.lower()}|{self.section.lower()}|{version.lower()}"

    def to_dict(self):
        return {
            "title": self.title,
            "section": self.section,
            "version": self.version,
            "subsection": self.subsection
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            title=data["title"],
            section=data["section"],
            version=data.get("version"),
            subsection=data.get("subsection")
        )
