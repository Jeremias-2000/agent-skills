import logging
from json import JSONDecodeError

import httpx

from app.mcp.application.configuration.settings import Settings, get_settings
from app.mcp.domain.exceptions import (
    PokemonApiResponseError,
    PokemonApiUnavailable,
    PokemonNotFound,
)
from app.mcp.domain.interfaces.adapters.pokemon_api import PokemonApi

logger = logging.getLogger(__name__)


class PokeApiClient(PokemonApi):
    def __init__(self, settings: Settings | None = None) -> None:
        configuration = settings or get_settings()
        self._base_url = configuration.pokeapi_base_url.rstrip("/")
        self._timeout = configuration.pokeapi_timeout

    async def get_pokemon(self, identifier: str) -> dict[str, object]:
        data = await self._request(f"pokemon/{identifier}")
        try:
            return {
                "id": data["id"],
                "name": data["name"],
                "height": data["height"],
                "weight": data["weight"],
                "base_experience": data["base_experience"],
                "types": [item["type"]["name"] for item in data["types"]],
                "abilities": [
                    item["ability"]["name"]
                    for item in data["abilities"]
                    if not item["is_hidden"]
                ],
                "stats": {
                    item["stat"]["name"]: item["base_stat"]
                    for item in data["stats"]
                },
                "sprite": data["sprites"]["front_default"],
            }
        except (JSONDecodeError, KeyError, TypeError) as error:
            raise PokemonApiResponseError(
                "PokéAPI returned an invalid Pokémon payload"
            ) from error

    async def get_resource(
        self, resource: str, identifier: str
    ) -> dict[str, object]:
        return await self._request(f"{resource}/{identifier}")

    async def list_resource(
        self, resource: str, limit: int, offset: int
    ) -> dict[str, object]:
        return await self._request(
            resource,
            params={"limit": str(limit), "offset": str(offset)},
        )

    async def get_pokemon_encounters(
        self, identifier: str
    ) -> list[dict[str, object]]:
        data = await self._request(f"pokemon/{identifier}/encounters")
        if not isinstance(data, list):
            raise PokemonApiResponseError(
                "PokéAPI returned an invalid encounters payload"
            )
        return data

    async def _request(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> dict[str, object] | list[dict[str, object]]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.get(f"{self._base_url}/{path}", params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as error:
                if error.response.status_code == 404:
                    logger.info("PokéAPI resource not found: %s", path)
                    raise PokemonNotFound(
                        f"PokéAPI resource '{path}' was not found"
                    ) from error
                logger.warning(
                    "PokéAPI returned HTTP %s for %s",
                    error.response.status_code,
                    path,
                )
                raise PokemonApiResponseError(
                    f"PokéAPI returned HTTP {error.response.status_code}"
                ) from error
            except httpx.RequestError as error:
                logger.warning("PokéAPI request failed for %s: %s", path, error)
                raise PokemonApiUnavailable("Could not connect to PokéAPI") from error

        try:
            data = response.json()
        except (JSONDecodeError, TypeError) as error:
            raise PokemonApiResponseError(
                "PokéAPI returned an invalid JSON payload"
            ) from error
        if not isinstance(data, (dict, list)):
            raise PokemonApiResponseError("PokéAPI returned an invalid payload")
        return data
