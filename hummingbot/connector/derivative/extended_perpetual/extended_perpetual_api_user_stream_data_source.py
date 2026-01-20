import asyncio
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import hummingbot.connector.derivative.extended_perpetual.extended_perpetual_constants as CONSTANTS
import hummingbot.connector.derivative.extended_perpetual.extended_perpetual_web_utils as web_utils
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.web_assistant.connections.data_types import WSJSONRequest
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.web_assistant.ws_assistant import WSAssistant
from hummingbot.logger import HummingbotLogger

if TYPE_CHECKING:
    from hummingbot.connector.derivative.extended_perpetual.extended_perpetual_auth import ExtendedPerpetualAuth
    from hummingbot.connector.derivative.extended_perpetual.extended_perpetual_derivative import (
        ExtendedPerpetualDerivative,
    )


class ExtendedPerpetualAPIUserStreamDataSource(UserStreamTrackerDataSource):
    """
    User stream data source for Extended Perpetual connector.
    Handles WebSocket connection for private account updates including:
    - Order updates
    - Trade fills
    - Balance updates
    - Position updates
    """

    HEARTBEAT_TIME_INTERVAL = 30.0
    _logger: Optional[HummingbotLogger] = None

    def __init__(
            self,
            auth: "ExtendedPerpetualAuth",
            trading_pairs: List[str],
            connector: "ExtendedPerpetualDerivative",
            api_factory: WebAssistantsFactory,
            domain: str = CONSTANTS.DEFAULT_DOMAIN,
    ):
        super().__init__()
        self._domain = domain
        self._api_factory = api_factory
        self._auth = auth
        self._connector = connector
        self._trading_pairs: List[str] = trading_pairs
        self._ping_task: Optional[asyncio.Task] = None
        self._last_recv_time: float = 0

    @property
    def last_recv_time(self) -> float:
        if self._ws_assistant:
            return self._ws_assistant.last_recv_time
        return self._last_recv_time

    async def _get_ws_assistant(self) -> WSAssistant:
        if self._ws_assistant is None:
            self._ws_assistant = await self._api_factory.get_ws_assistant()
        return self._ws_assistant

    async def _connected_websocket_assistant(self) -> WSAssistant:
        """
        Creates an instance of WSAssistant connected to the exchange user stream endpoint.
        Authentication is done via headers (X-Api-Key and User-Agent).
        """
        ws: WSAssistant = await self._get_ws_assistant()

        ws_url = web_utils.wss_url(CONSTANTS.WS_ACCOUNT_PATH, self._domain)

        headers = {
            CONSTANTS.API_KEY_HEADER: self._auth.api_key,
            CONSTANTS.USER_AGENT_HEADER: CONSTANTS.DEFAULT_USER_AGENT,
        }

        await ws.connect(
            ws_url=ws_url,
            ping_timeout=CONSTANTS.HEARTBEAT_TIME_INTERVAL,
            ws_headers=headers,
        )

        self._start_ping_task(ws)

        self.logger().info(f"Connected to Extended Perpetual user stream: {ws_url}")
        return ws

    async def _subscribe_channels(self, websocket_assistant: WSAssistant):
        """
        No explicit subscription needed - server sends all account updates
        automatically upon connection after authentication.
        Initial snapshot is sent on connect with balance, positions, and orders.
        """
        self.logger().info("Subscribed to Extended Perpetual private user stream channels")

    async def _process_event_message(self, event_message: Dict[str, Any], queue: asyncio.Queue):
        """
        Processes incoming WebSocket messages and routes them to the queue.
        
        Message types:
        - orders: Order status updates
        - trades: Trade/fill updates
        - balance: Account balance updates
        - positions: Position updates
        - ping: Heartbeat from server (respond with pong)
        """
        if event_message is None or len(event_message) == 0:
            return

        if "ping" in event_message:
            return

        if "error" in event_message:
            err_msg = event_message.get("error", {})
            if isinstance(err_msg, dict):
                err_msg = err_msg.get("message", str(event_message.get("error")))
            raise IOError({
                "label": "WSS_ERROR",
                "message": f"Error received via websocket - {err_msg}."
            })

        if any(key in event_message for key in ["orders", "trades", "balance", "positions"]):
            queue.put_nowait(event_message)

    async def _process_websocket_messages(self, websocket_assistant: WSAssistant, queue: asyncio.Queue):
        """
        Processes websocket messages and handles ping/pong keepalive.
        Server sends ping every 15s, must respond within 10s.
        """
        while True:
            try:
                async for ws_response in websocket_assistant.iter_messages():
                    data = ws_response.data
                    
                    if isinstance(data, dict) and "ping" in data:
                        await self._send_pong(websocket_assistant, data.get("ping"))
                        continue
                    
                    await self._process_event_message(event_message=data, queue=queue)
            except asyncio.TimeoutError:
                ping_request = WSJSONRequest(payload={"type": "ping"})
                await websocket_assistant.send(ping_request)

    async def _send_pong(self, websocket_assistant: WSAssistant, ping_id: Any = None):
        """
        Responds to server ping with pong message.
        """
        pong_payload = {"pong": ping_id} if ping_id else {"pong": True}
        pong_request = WSJSONRequest(payload=pong_payload)
        await websocket_assistant.send(pong_request)

    def _start_ping_task(self, websocket_assistant: WSAssistant):
        """
        Starts background task to send periodic pings to keep connection alive.
        """
        if self._ping_task is not None and not self._ping_task.done():
            self._ping_task.cancel()
        self._ping_task = asyncio.create_task(self._ping_loop(websocket_assistant))

    async def _ping_loop(self, websocket_assistant: WSAssistant):
        """
        Sends periodic ping messages to keep the WebSocket connection alive.
        """
        try:
            while True:
                await asyncio.sleep(CONSTANTS.PING_INTERVAL)
                ping_request = WSJSONRequest(payload={"type": "ping"})
                await websocket_assistant.send(ping_request)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger().debug(f"Ping loop error: {e}")

    async def _on_user_stream_interruption(self, websocket_assistant: Optional[WSAssistant]):
        """
        Cleans up resources when the user stream is interrupted.
        """
        if self._ping_task is not None and not self._ping_task.done():
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
            self._ping_task = None

        await super()._on_user_stream_interruption(websocket_assistant)

    async def stop(self):
        """
        Stops the user stream data source and cleans up resources.
        """
        if self._ping_task is not None and not self._ping_task.done():
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
            self._ping_task = None

        await super().stop()
