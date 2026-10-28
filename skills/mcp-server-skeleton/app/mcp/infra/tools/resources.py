from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from app.mcp.application.usecases.pokeapi_resources import PokeApiResourcesUseCase


READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
PageSize = Annotated[int, Field(default=20, ge=1, le=100)]
PageOffset = Annotated[int, Field(default=0, ge=0)]


def register_resource_tools(
    server: MCPServer,
    resources: PokeApiResourcesUseCase,
) -> None:
    @server.tool(
        title="Get Pokémon species",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def get_pokemon_species(pokemon: str) -> dict[str, object]:
        """Return species metadata, descriptions, breeding, and generation data."""
        return await resources.get("pokemon-species", pokemon)

    @server.tool(
        title="Get Pokémon evolution",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def get_pokemon_evolution(pokemon: str) -> dict[str, object]:
        """Return the evolution chain for a Pokémon."""
        species = await resources.get("pokemon-species", pokemon)
        chain = species.get("evolution_chain")
        if not isinstance(chain, dict) or not isinstance(chain.get("url"), str):
            return {"species": species, "evolution_chain": None}
        chain_id = chain["url"].rstrip("/").split("/")[-1]
        return {
            "pokemon": pokemon,
            "evolution_chain": await resources.get("evolution-chain", chain_id),
        }

    @server.tool(
        title="Get type matchups",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def get_type_matchups(pokemon_type: str) -> dict[str, object]:
        """Return type damage relations for a Pokémon type."""
        data = await resources.get("type", pokemon_type)
        return {
            "id": data["id"],
            "name": data["name"],
            "damage_relations": data["damage_relations"],
        }

    @server.tool(
        title="Get move details",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def get_move_details(move: str) -> dict[str, object]:
        """Return details for a Pokémon move."""
        return await resources.get("move", move)

    @server.tool(
        title="Get ability details",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def get_ability_details(ability: str) -> dict[str, object]:
        """Return details and Pokémon associated with an ability."""
        return await resources.get("ability", ability)

    @server.tool(
        title="Get item details",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def get_item_details(item: str) -> dict[str, object]:
        """Return details for a Pokémon item."""
        return await resources.get("item", item)

    @server.tool(
        title="Get Pokémon encounters",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def get_pokemon_encounters(pokemon: str) -> list[dict[str, object]]:
        """Return locations and conditions where a Pokémon can be encountered."""
        return await resources.encounters(pokemon)

    @server.tool(
        title="Get location details",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def get_location_details(location: str) -> dict[str, object]:
        """Return details for a Pokémon world location."""
        return await resources.get("location", location)

    @server.tool(
        title="Get location encounters",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def get_location_encounters(
        location_area: str,
    ) -> dict[str, object]:
        """Return Pokémon encounter data for a location area."""
        return await resources.get("location-area", location_area)

    @server.tool(
        title="Get Pokémon forms",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def get_pokemon_forms(pokemon: str) -> dict[str, object]:
        """Return alternate form details for a Pokémon."""
        return await resources.get("pokemon-form", pokemon)

    @server.tool(
        title="Compare Pokémon",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def compare_pokemon(
        first: str, second: str
    ) -> dict[str, object]:
        """Return details for two Pokémon for client-side comparison."""
        return await resources.compare(first, second)

    @server.tool(
        title="List Pokémon",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def list_pokemon(
        limit: PageSize = 20, offset: PageOffset = 0
    ) -> dict[str, object]:
        """Return a paginated list of Pokémon."""
        return await resources.list_resource("pokemon", limit, offset)

    @server.tool(
        title="List moves",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def list_moves(
        limit: PageSize = 20, offset: PageOffset = 0
    ) -> dict[str, object]:
        """Return a paginated list of moves."""
        return await resources.list_resource("move", limit, offset)

    @server.tool(
        title="List abilities",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def list_abilities(
        limit: PageSize = 20, offset: PageOffset = 0
    ) -> dict[str, object]:
        """Return a paginated list of abilities."""
        return await resources.list_resource("ability", limit, offset)

    @server.tool(
        title="List items",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def list_items(
        limit: PageSize = 20, offset: PageOffset = 0
    ) -> dict[str, object]:
        """Return a paginated list of items."""
        return await resources.list_resource("item", limit, offset)

    @server.tool(
        title="List locations",
        annotations=READ_ONLY,
        structured_output=True,
    )
    async def list_locations(
        limit: PageSize = 20, offset: PageOffset = 0
    ) -> dict[str, object]:
        """Return a paginated list of locations."""
        return await resources.list_resource("location", limit, offset)
