"""Platform adapters for social media publishing."""

from .base import BasePlatform
from .twitter import TwitterPlatform

__all__ = ["BasePlatform", "TwitterPlatform"]
