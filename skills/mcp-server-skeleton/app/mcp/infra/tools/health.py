import logging

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context

logger = logging.getLogger(__name__)


def register_health_tools(server: MCPServer) -> None:
    @server.tool()
    def health_check(ctx: Context) -> str:
        """Return the server health status."""
        logger.info("health_check called", extra={"request_id": ctx.request_id})
        return "ok"
