"""
This module defines the BaseConfig abstract class, which extends the Mapping interface
for reading configuration data from an underlying dictionary-like object.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping


class BaseConfig(ABC, Mapping):
    """
    Abstract base class for configuration objects.
    Subclasses must implement the dump method to provide
    access to an internal dictionary-like data structure.
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
        Return the value associated with the specified key.
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
