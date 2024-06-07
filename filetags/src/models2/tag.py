class Tag:
    def __init__(self, name, children=None):
        self.name = name
        self.children = children or []

    def __str__(self):
        kids = ",".join(
            str(child) for child in sorted(self.children, key=lambda x: x.name)
        )
        return f"{self.name}" + (f"[{kids}]" if kids else "")

    def __repr__(self):
        return f"Tag({self})"

    def __json__(self):
        return {"name": self.name, "children": self.children}
