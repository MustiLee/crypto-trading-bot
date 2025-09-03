import asyncio
import json
from datetime import datetime
from typing import Dict, List
from pathlib import Path
import yaml

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from loguru import logger

from .multi_symbol_stream import MultiSymbolBinanceStream
from .live_signals import LiveSignalGenerator, SignalType

# Import mobile API router
try:
    from ..api.mobile_api import mobile_router
    API_AVAILABLE = True
    logger.info("Mobile API routes loaded successfully")
except ImportError as e:
    mobile_router = None
    API_AVAILABLE = False
    logger.warning(f"Mobile API routes not available: {e}")

# Try to import auth router, but don't fail if dependencies missing
# Temporarily disabled for testing
auth_router = None
AUTH_AVAILABLE = False
logger.warning("Authentication routes disabled for testing")


class MultiSymbolWebSocketManager:
    """Manage WebSocket connections for multiple symbols"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, data: dict):
        """Broadcast data to all connected clients"""
        if not self.active_connections:
            logger.debug("No active WebSocket connections to broadcast to")
            return
            
        message = json.dumps(data)
        disconnected = []
        
        logger.debug(f"Broadcasting message to {len(self.active_connections)} connections")
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
                logger.debug("Successfully sent WebSocket message")
            except Exception as e:
                logger.warning(f"Error sending to WebSocket client: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


class MultiSymbolTradingDashboard:
    """Multi-symbol real-time trading dashboard"""
    
    def __init__(self, interval: str = "5m", port: int = 8000):
        self.app = FastAPI(title="Multi-Symbol Trading Dashboard")
        self.port = port
        self.interval = interval
        
        # Load symbols configuration
        config_path = Path(__file__).parent.parent.parent / "config" / "symbols.yaml"
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.symbols = self.config['symbols']
        
        # WebSocket manager
        self.ws_manager = MultiSymbolWebSocketManager()
        
        # Multi-symbol stream
        self.stream = MultiSymbolBinanceStream(interval=interval)
        
        # Signal generators for each symbol
        self.signal_generators = {}
        for symbol_key, symbol_config in self.symbols.items():
            try:
                strategy_config_path = f"config/strategy.{symbol_config['strategy']}.yaml"
                self.signal_generators[symbol_key] = LiveSignalGenerator(
                    symbol=symbol_config['symbol'],
                    interval=interval,
                    strategy_config_path=strategy_config_path
                )
                
                # Add callback to stream
                self.stream.add_callback(symbol_key, self._on_symbol_update)
                
            except Exception as e:
                logger.error(f"Failed to initialize signal generator for {symbol_key}: {e}")
        
        # Setup routes
        self._setup_routes()
        
        # Include authentication and strategy testing routes if available
        if AUTH_AVAILABLE and auth_router:
            self.app.include_router(auth_router)
            logger.info("Authentication routes included")
        else:
            logger.warning("Authentication routes not available - running without user management")
        
        # Include mobile API routes
        if API_AVAILABLE and mobile_router:
            self.app.include_router(mobile_router)
            logger.info("Mobile API routes included")
        else:
            logger.warning("Mobile API routes not available")
        
        logger.info(f"Initialized multi-symbol dashboard for: {list(self.symbols.keys())}")
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
            return self._get_multi_symbol_html()
        
        if AUTH_AVAILABLE:
            @self.app.get("/strategy-tester", response_class=HTMLResponse)
            async def strategy_tester():
                """Serve the strategy tester page"""
                return self._get_strategy_tester_html()
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.ws_manager.connect(websocket)
            try:
                while True:
                    # Keep connection alive
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.ws_manager.disconnect(websocket)
        
        @self.app.get("/api/symbols")
        async def get_symbols():
            """Get list of configured symbols"""
            return {
                "symbols": self.symbols,
                "interval": self.interval
            }
        
        @self.app.get("/api/signals/{symbol_key}")
        async def get_signals(symbol_key: str):
            """Get recent signals for a symbol"""
            if symbol_key in self.signal_generators:
                # Get recent signals from database
                from ..database.db_manager import TradingDBManager
                db = TradingDBManager()
                signals = db.get_recent_signals(limit=10)
                
                # Filter for this symbol
                symbol_signals = [s for s in signals if s['symbol'] == self.symbols[symbol_key]['symbol']]
                return {"signals": symbol_signals}
            return {"error": "Symbol not found"}
    
    async def _on_symbol_update(self, symbol_key: str, kline_data: dict):
        """Handle updates from symbol stream"""
        try:
            if symbol_key not in self.signal_generators:
                return
                
            # Process through signal generator
            signal_generator = self.signal_generators[symbol_key]
            await signal_generator._on_new_kline(kline_data)
            
            # Get latest signal info
            current_signal = getattr(signal_generator, 'current_signal', SignalType.NEUTRAL)
            latest_indicators = getattr(signal_generator, 'latest_indicators', {})
            
            # Broadcast update to dashboard
            update_data = {
                'type': 'symbol_update',
                'symbol': symbol_key,
                'data': {
                    'price': kline_data['close'],
                    'timestamp': kline_data['timestamp'].isoformat(),
                    'signal': current_signal.value if hasattr(current_signal, 'value') else str(current_signal),
                    'indicators': {
                        'RSI': latest_indicators.get('RSI', 0),
                        'MACD': latest_indicators.get('MACD', 0),
                        'BB_UPPER': latest_indicators.get('BBU', 0),
                        'BB_LOWER': latest_indicators.get('BBL', 0)
                    },
                    'is_closed': kline_data['is_closed']
                }
            }
            
            await self.ws_manager.broadcast(update_data)
            
        except Exception as e:
            logger.error(f"Error processing symbol update for {symbol_key}: {e}")
    
    def _get_multi_symbol_html(self) -> str:
        """Generate multi-symbol dashboard HTML"""
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Symbol Trading Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .dashboard {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            color: white;
        }}
        
        .symbols-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }}
        
        .symbol-card {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }}
        
        .symbol-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        
        .symbol-name {{
            font-size: 1.5rem;
            font-weight: 600;
        }}
        
        .price-display {{
            font-size: 2rem;
            font-weight: 700;
            color: #2563eb;
        }}
        
        .signal-indicator {{
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.9rem;
        }}
        
        .signal-buy {{ background: #10b981; color: white; }}
        .signal-sell {{ background: #ef4444; color: white; }}
        .signal-neutral {{ background: #6b7280; color: white; }}
        
        .indicators-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-top: 20px;
        }}
        
        .indicator {{
            background: #f8fafc;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }}
        
        .indicator-label {{
            font-size: 0.8rem;
            color: #64748b;
            margin-bottom: 5px;
        }}
        
        .indicator-value {{
            font-size: 1.2rem;
            font-weight: 600;
            color: #1e293b;
        }}
        
        .last-update {{
            margin-top: 15px;
            font-size: 0.8rem;
            color: #64748b;
            text-align: center;
        }}
        
        .connection-status {{
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 15px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }}
        
        .status-connected {{ background: #10b981; color: white; }}
        .status-disconnected {{ background: #ef4444; color: white; }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>🚀 Multi-Symbol Trading Dashboard</h1>
            <p>Real-time cryptocurrency analysis for BTC, ETH & XRP</p>
            <div style="margin-top: 15px;">
                {f'<a href="/strategy-tester" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 10px 20px; border-radius: 20px; font-weight: bold;">🧪 Strateji Test</a>' if AUTH_AVAILABLE else '<span style="background: #666; color: white; padding: 10px 20px; border-radius: 20px; opacity: 0.5;">🧪 Strateji Test (Yakında)</span>'}
            </div>
        </div>
        
        <div id="connectionStatus" class="connection-status status-disconnected">
            🔴 Disconnected
        </div>
        
        <div class="symbols-grid" id="symbolsGrid">
            <!-- Symbol cards will be populated by JavaScript -->
        </div>
    </div>

    <script>
        class MultiSymbolDashboard {{
            constructor() {{
                this.symbols = {json.dumps(list(self.symbols.keys()))};
                this.symbolData = {{}};
                this.ws = null;
                this.reconnectInterval = null;
                
                this.initializeSymbols();
                this.connectWebSocket();
            }}
            
            initializeSymbols() {{
                const grid = document.getElementById('symbolsGrid');
                
                this.symbols.forEach(symbol => {{
                    this.symbolData[symbol] = {{
                        price: 0,
                        signal: 'NEUTRAL',
                        indicators: {{RSI: 0, MACD: 0, BB_UPPER: 0, BB_LOWER: 0}},
                        lastUpdate: null
                    }};
                    
                    const card = this.createSymbolCard(symbol);
                    grid.appendChild(card);
                }});
            }}
            
            createSymbolCard(symbol) {{
                const symbolConfig = {json.dumps(self.symbols)};
                const config = symbolConfig[symbol];
                
                const card = document.createElement('div');
                card.className = 'symbol-card';
                card.innerHTML = `
                    <div class="symbol-header">
                        <div>
                            <div class="symbol-name">${{config.display_name}} (${{symbol}})</div>
                            <div class="price-display" id="price-${{symbol}}">$0.00</div>
                        </div>
                        <div class="signal-indicator signal-neutral" id="signal-${{symbol}}">
                            NEUTRAL
                        </div>
                    </div>
                    
                    <div class="indicators-grid">
                        <div class="indicator">
                            <div class="indicator-label">RSI</div>
                            <div class="indicator-value" id="rsi-${{symbol}}">0.0</div>
                        </div>
                        <div class="indicator">
                            <div class="indicator-label">MACD</div>
                            <div class="indicator-value" id="macd-${{symbol}}">0.0</div>
                        </div>
                        <div class="indicator">
                            <div class="indicator-label">BB Upper</div>
                            <div class="indicator-value" id="bb-upper-${{symbol}}">0.0</div>
                        </div>
                        <div class="indicator">
                            <div class="indicator-label">BB Lower</div>
                            <div class="indicator-value" id="bb-lower-${{symbol}}">0.0</div>
                        </div>
                    </div>
                    
                    <div class="last-update" id="update-${{symbol}}">
                        No updates yet
                    </div>
                `;
                
                return card;
            }}
            
            connectWebSocket() {{
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${{protocol}}//${{window.location.host}}/ws`;
                
                this.ws = new WebSocket(wsUrl);
                
                this.ws.onopen = () => {{
                    console.log('WebSocket connected');
                    this.updateConnectionStatus(true);
                    if (this.reconnectInterval) {{
                        clearInterval(this.reconnectInterval);
                        this.reconnectInterval = null;
                    }}
                }};
                
                this.ws.onmessage = (event) => {{
                    const data = JSON.parse(event.data);
                    this.handleUpdate(data);
                }};
                
                this.ws.onclose = () => {{
                    console.log('WebSocket disconnected');
                    this.updateConnectionStatus(false);
                    this.scheduleReconnect();
                }};
                
                this.ws.onerror = (error) => {{
                    console.error('WebSocket error:', error);
                    this.updateConnectionStatus(false);
                }};
            }}
            
            handleUpdate(data) {{
                if (data.type === 'symbol_update') {{
                    this.updateSymbolData(data.symbol, data.data);
                }}
            }}
            
            updateSymbolData(symbol, data) {{
                // Update price
                const priceEl = document.getElementById(`price-${{symbol}}`);
                if (priceEl) {{
                    priceEl.textContent = `$` + parseFloat(data.price).toLocaleString('en-US', {{
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 8
                    }});
                }}
                
                // Update signal
                const signalEl = document.getElementById(`signal-${{symbol}}`);
                if (signalEl) {{
                    signalEl.textContent = data.signal;
                    signalEl.className = `signal-indicator signal-${{data.signal.toLowerCase()}}`;
                }}
                
                // Update indicators
                if (data.indicators) {{
                    ['rsi', 'macd', 'bb-upper', 'bb-lower'].forEach(indicator => {{
                        const el = document.getElementById(`${{indicator}}-${{symbol}}`);
                        if (el) {{
                            const key = indicator.toUpperCase().replace('-', '_');
                            const value = data.indicators[key] || 0;
                            el.textContent = parseFloat(value).toFixed(2);
                        }}
                    }});
                }}
                
                // Update timestamp
                const updateEl = document.getElementById(`update-${{symbol}}`);
                if (updateEl) {{
                    updateEl.textContent = `Last update: ${{new Date(data.timestamp).toLocaleTimeString()}}`;
                }}
            }}
            
            updateConnectionStatus(connected) {{
                const statusEl = document.getElementById('connectionStatus');
                if (connected) {{
                    statusEl.textContent = '🟢 Connected';
                    statusEl.className = 'connection-status status-connected';
                }} else {{
                    statusEl.textContent = '🔴 Disconnected';
                    statusEl.className = 'connection-status status-disconnected';
                }}
            }}
            
            scheduleReconnect() {{
                if (!this.reconnectInterval) {{
                    this.reconnectInterval = setInterval(() => {{
                        console.log('Attempting to reconnect...');
                        this.connectWebSocket();
                    }}, 5000);
                }}
            }}
        }}
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', () => {{
            new MultiSymbolDashboard();
        }});
    </script>
</body>
</html>'''
    
    async def start(self):
        """Start the dashboard server and stream"""
        # Initialize all signal generators first
        logger.info("Initializing signal generators for all symbols...")
        for symbol_key, signal_generator in self.signal_generators.items():
            try:
                logger.info(f"Initializing {symbol_key} signal generator...")
                await signal_generator.initialize()
                logger.info(f"✅ {symbol_key} signal generator initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize {symbol_key} signal generator: {e}")
        
        # Start the stream in background
        stream_task = asyncio.create_task(self.stream.connect())
        
        # Start the web server
        config = uvicorn.Config(
            app=self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        try:
            await server.serve()
        finally:
            await self.stream.disconnect()
    
    def _get_strategy_tester_html(self) -> str:
        """Generate strategy tester HTML"""
        try:
            # Read the strategy tester HTML file
            html_path = Path(__file__).parent.parent.parent / "templates" / "strategy_tester.html"
            with open(html_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Strategy tester HTML file not found at {html_path}")
            return """
            <html>
                <head><title>Strategy Tester - File Not Found</title></head>
                <body>
                    <h1>Strategy Tester HTML file not found</h1>
                    <p>Please ensure the strategy_tester.html file exists in the templates directory.</p>
                    <a href="/">Back to Dashboard</a>
                </body>
            </html>
            """
        except Exception as e:
            logger.error(f"Error loading strategy tester HTML: {e}")
            return """
            <html>
                <head><title>Strategy Tester - Error</title></head>
                <body>
                    <h1>Error loading Strategy Tester</h1>
                    <p>An error occurred while loading the strategy tester.</p>
                    <a href="/">Back to Dashboard</a>
                </body>
            </html>
            """
    
    async def stop(self):
        """Stop the dashboard"""
        await self.stream.disconnect()
        logger.info("Multi-symbol dashboard stopped")