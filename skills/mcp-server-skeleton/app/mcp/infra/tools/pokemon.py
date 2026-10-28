import logging

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context

from app.mcp.application.usecases.get_pokemon_details import (
    GetPokemonDetailsUseCase,
)

logger = logging.getLogger(__name__)


def register_pokemon_tools(
    server: MCPServer,
    get_pokemon_details_usecase: GetPokemonDetailsUseCase,
) -> None:
    @server.tool()
    async def get_pokemon_details(
        pokemon: str, ctx: Context
    ) -> dict[str, object]:
        """Return details for a Pokémon identified by name or Pokédex ID."""
        logger.info(
            "get_pokemon_details called with pokemon=%s",
            pokemon,
            extra={"request_id": ctx.request_id},
        )
        return await get_pokemon_details_usecase.execute(pokemon)
