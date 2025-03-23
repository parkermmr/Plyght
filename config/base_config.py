from collections.abc import Mapping


class BaseConfig(Mapping):
    def dump(self):
        raise NotImplementedError("Subclasses must implement dump")

    def __getitem__(self, key):
        return self.dump()[key]

    def __iter__(self):
        return iter(self.dump())

    def __len__(self):
        return len(self.dump())
