class WebSocketManager:
    def __init__(self):
        self.active_websockets = {}

    def add_websocket(self, websocket):
        self.active_websockets[id(websocket)] = websocket

    def remove_websocket(self, websocket):
        self.active_websockets.pop(id(websocket), None)

    async def broadcast_game_info(self, game_info):
        for websocket in self.active_websockets.values():
            await websocket.send_json(game_info.dict())

# 创建一个全局的 WebSocket 管理器实例
websocket_manager = WebSocketManager()