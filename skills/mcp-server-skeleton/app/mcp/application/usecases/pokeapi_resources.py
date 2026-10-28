from __future__ import annotations

import asyncio

from app.mcp.domain.exceptions import InvalidPokemonIdentifier
from app.mcp.domain.interfaces.adapters.pokemon_api import PokemonApi


class PokeApiResourcesUseCase:
    def __init__(self, pokemon_api: PokemonApi) -> None:
        self._pokemon_api = pokemon_api

    async def get(self, resource: str, identifier: str) -> dict[str, object]:
        return await self._pokemon_api.get_resource(
            resource, self._identifier(identifier)
        )

    async def list_resource(
        self, resource: str, limit: int = 20, offset: int = 0
    ) -> dict[str, object]:
        if limit < 1 or limit > 100:
            raise InvalidPokemonIdentifier("limit must be between 1 and 100")
        if offset < 0:
            raise InvalidPokemonIdentifier("offset must be zero or greater")
        return await self._pokemon_api.list_resource(resource, limit, offset)

    async def encounters(self, identifier: str) -> list[dict[str, object]]:
        return await self._pokemon_api.get_pokemon_encounters(
            self._identifier(identifier)
        )

    async def compare(
        self, first: str, second: str
    ) -> dict[str, object]:
        first_data, second_data = await asyncio.gather(
            self._pokemon_api.get_pokemon(self._identifier(first)),
            self._pokemon_api.get_pokemon(self._identifier(second)),
        )
        return {"first": first_data, "second": second_data}

    @staticmethod
    def _identifier(value: str) -> str:
        identifier = value.strip().lower()
        if not identifier or (
            not identifier.isdigit()
            and not identifier.replace("-", "").isalnum()
        ):
            raise InvalidPokemonIdentifier(
                "identifier must contain only letters, numbers, or hyphens"
            )
        return identifier
