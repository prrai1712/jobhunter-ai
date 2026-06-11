"""Provider registry — factory for ATS providers (adapter pattern)."""

from __future__ import annotations

from typing import Type

from src.providers.base import ATSProvider


class ProviderRegistry:
    """Registry and factory for ATS provider adapters.

    Supports dynamic registration so new providers can be added
    without modifying existing code.
    """

    _providers: dict[str, Type[ATSProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: Type[ATSProvider]) -> None:
        """Register a provider class by name."""
        cls._providers[name.lower()] = provider_class

    @classmethod
    def get_provider(cls, name: str) -> ATSProvider:
        """Get an instance of a provider by name.

        Raises:
            ValueError: If the provider name is not registered.
        """
        name_lower = name.lower()
        if name_lower not in cls._providers:
            raise ValueError(
                f"Unknown provider '{name}'. "
                f"Available: {list(cls._providers.keys())}"
            )
        return cls._providers[name_lower]()

    @classmethod
    def get_all_providers(cls) -> dict[str, ATSProvider]:
        """Get instances of all registered providers."""
        return {name: cls() for name, cls in cls._providers.items()}

    @classmethod
    def available_providers(cls) -> list[str]:
        """List names of all registered providers."""
        return list(cls._providers.keys())


def register_all_providers() -> None:
    """Import and register all built-in providers."""
    from src.providers.greenhouse import GreenhouseProvider
    from src.providers.lever import LeverProvider
    from src.providers.ashby import AshbyProvider

    ProviderRegistry.register("greenhouse", GreenhouseProvider)
    ProviderRegistry.register("lever", LeverProvider)
    ProviderRegistry.register("ashby", AshbyProvider)
