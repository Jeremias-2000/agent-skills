import sys
from pathlib import Path


_app_directory = str(Path(__file__).resolve().parents[3])
if _app_directory in sys.path:
    sys.path.remove(_app_directory)

from mcp.server.mcpserver import MCPServer

from app.mcp.application.configuration.settings import get_settings
from app.mcp.application.usecases.get_pokemon_details import (
    GetPokemonDetailsUseCase,
)
from app.mcp.application.usecases.pokeapi_resources import (
    PokeApiResourcesUseCase,
)
from app.mcp.domain.interfaces.adapters.pokemon_api import PokemonApi
from app.mcp.infra.adapters.pokeapi_client import PokeApiClient
from app.mcp.infra.logging import load_logging_config
from app.mcp.infra.tools.registry import register_tools

load_logging_config()


def create_server() -> MCPServer:
    settings = get_settings()
    pokemon_api: PokemonApi = PokeApiClient(settings)
    get_pokemon_details = GetPokemonDetailsUseCase(pokemon_api)
    resources = PokeApiResourcesUseCase(pokemon_api)
    server = MCPServer(name="mcp-server-skeleton")
    register_tools(server, get_pokemon_details, resources)
    return server


mcp = create_server()
app = mcp.streamable_http_app()
