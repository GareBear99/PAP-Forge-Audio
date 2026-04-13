"""Compatibility shim for the old package name."""
from pap import PAPProject as ForgeProject, PluginSpec
__all__ = ["ForgeProject", "PluginSpec"]
