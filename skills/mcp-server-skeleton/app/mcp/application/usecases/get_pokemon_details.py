from app.mcp.domain.exceptions import InvalidPokemonIdentifier
from app.mcp.domain.interfaces.adapters.pokemon_api import PokemonApi


class GetPokemonDetailsUseCase:
    def __init__(self, pokemon_api: PokemonApi) -> None:
        self._pokemon_api = pokemon_api

    async def execute(self, pokemon: str) -> dict[str, object]:
        identifier = pokemon.strip().lower()
        if not identifier:
            raise InvalidPokemonIdentifier(
                "pokemon must contain a name or Pokédex ID"
            )
        if not identifier.isdigit() and not identifier.replace("-", "").isalnum():
            raise InvalidPokemonIdentifier(
                "pokemon must contain only letters, numbers, or hyphens"
            )

        return await self._pokemon_api.get_pokemon(identifier)
