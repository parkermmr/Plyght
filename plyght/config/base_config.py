"""
Defines the BaseConfig abstract class, which extends the Mapping interface
for reading configuration data from a dictionary-like object. Subclasses
must implement the dump method to provide access to the underlying data.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping


class BaseConfig(ABC, Mapping):
    """
    Abstract base class for configuration objects. Subclasses must implement
    the dump method, returning the underlying data as a dictionary-like object.
    """

    @abstractmethod
    def dump(self):
        """
        Return the underlying configuration data as a dictionary-like object.
        Must be implemented by subclasses.
        """
        pass

    def __getitem__(self, key):
        """
        Retrieve the value associated with the given key from the configuration.
        """
        return self.dump()[key]

    def __iter__(self):
        """
        Return an iterator over the configuration keys.
        """
        return iter(self.dump())

    def __len__(self):
        """
        Return the number of items in the configuration.
        """
        return len(self.dump())
