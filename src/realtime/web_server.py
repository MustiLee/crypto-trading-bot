import asyncio
import json
from datetime import datetime
from typing import Dict, List
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from loguru import logger

from .live_signals import LiveSignalGenerator, SignalType


class WebSocketManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    @property
    def connections(self) -> List[WebSocket]:
        """Get list of active connections"""
        return self.active_connections
    
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


class TradingDashboardServer:
    """Real-time trading dashboard web server"""
    
    def __init__(self, symbol: str = "btcusdt", interval: str = "5m", port: int = 8000):
        self.app = FastAPI(title="Live Trading Dashboard")
        self.port = port
        
        # WebSocket manager
        self.ws_manager = WebSocketManager()
        
        # Live signal generator
        self.signal_generator = LiveSignalGenerator(
            symbol=symbol, 
            interval=interval,
            strategy_config_path="config/strategy.realistic1.yaml"
        )
        
        # Setup routes
        self._setup_routes()
        
        logger.info(f"Trading dashboard server initialized for {symbol.upper()} {interval}")
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard():
            """Serve the main dashboard page"""
            return self._get_dashboard_html()
        
        @self.app.get("/api/market-data")
        async def get_market_data():
            """Get current market data"""
            return self.signal_generator.get_current_market_data()
        
        @self.app.get("/api/signals")
        async def get_signals():
            """Get signal history"""
            return {
                "signals": self.signal_generator.get_signal_history(),
                "current_signal": self.signal_generator.last_signal.value if self.signal_generator.last_signal else "NEUTRAL"
            }
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await self.ws_manager.connect(websocket)
            try:
                # Send initial data with market data and signal history
                market_data = self.signal_generator.get_current_market_data()
                signal_history = self.signal_generator.get_signal_history()
                
                initial_data = {
                    "type": "initial",
                    "data": {
                        **market_data,
                        "signal_history": signal_history
                    }
                }
                await websocket.send_text(json.dumps(initial_data))
                
                # Keep connection alive
                while True:
                    await websocket.receive_text()
                    
            except WebSocketDisconnect:
                self.ws_manager.disconnect(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.ws_manager.disconnect(websocket)
    
    async def _on_signal_update(self, signal_data: Dict):
        """Handle signal updates from LiveSignalGenerator"""
        try:
            # Determine update type - price update or signal change
            update_type = "price_update" if signal_data.get('is_price_update', False) else "signal"
            
            # Broadcast update to all WebSocket clients
            update_data = {
                "type": update_type,
                "data": signal_data
            }
            
            logger.debug(f"Broadcasting {update_type} to {len(self.ws_manager.connections)} clients: ${signal_data.get('price', 'N/A')}")
            await self.ws_manager.broadcast(update_data)
            
        except Exception as e:
            logger.error(f"Error broadcasting signal update: {e}")
    
    async def _on_market_update(self, kline_data: Dict):
        """Handle market data updates"""
        try:
            # Get current market data with indicators
            market_data = self.signal_generator.get_current_market_data()
            
            if market_data:
                update_data = {
                    "type": "market",
                    "data": market_data
                }
                await self.ws_manager.broadcast(update_data)
                
        except Exception as e:
            logger.error(f"Error broadcasting market update: {e}")
    
    def _get_dashboard_html(self) -> str:
        """Generate dashboard HTML"""
        return '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Live Trading Dashboard - Realistic1 Strategy</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }
        
        .dashboard {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            color: #2c3e50;
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        
        .header .subtitle {
            color: #7f8c8d;
            font-size: 1.1rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.95);
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
        }
        
        .card h2 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.4rem;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        
        .signal-display {
            text-align: center;
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 20px;
            font-size: 2rem;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 2px;
            transition: all 0.3s ease;
        }
        
        .signal-buy {
            background: linear-gradient(45deg, #27ae60, #2ecc71);
            color: white;
            animation: pulse-green 2s infinite;
        }
        
        .signal-sell {
            background: linear-gradient(45deg, #e74c3c, #c0392b);
            color: white;
            animation: pulse-red 2s infinite;
        }
        
        .signal-neutral {
            background: linear-gradient(45deg, #95a5a6, #7f8c8d);
            color: white;
        }
        
        @keyframes pulse-green {
            0% { box-shadow: 0 0 0 0 rgba(46, 204, 113, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(46, 204, 113, 0); }
            100% { box-shadow: 0 0 0 0 rgba(46, 204, 113, 0); }
        }
        
        @keyframes pulse-red {
            0% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(231, 76, 60, 0); }
            100% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0); }
        }
        
        .price-display {
            font-size: 3rem;
            font-weight: bold;
            text-align: center;
            color: #2c3e50;
            margin: 20px 0;
        }
        
        .price-change {
            text-align: center;
            font-size: 1.2rem;
            margin-top: 10px;
        }
        
        .price-up { color: #27ae60; }
        .price-down { color: #e74c3c; }
        
        @keyframes flashGreen {
            0% { background-color: transparent; }
            50% { background-color: rgba(39, 174, 96, 0.3); }
            100% { background-color: transparent; }
        }
        
        @keyframes flashRed {
            0% { background-color: transparent; }
            50% { background-color: rgba(231, 76, 60, 0.3); }
            100% { background-color: transparent; }
        }
        
        .indicator-value.overbought { color: #e74c3c; font-weight: bold; }
        .indicator-value.oversold { color: #27ae60; font-weight: bold; }
        .indicator-value.neutral { color: #34495e; }
        
        .indicator-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        .indicator {
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
            text-align: center;
        }
        
        .indicator-label {
            font-size: 0.9rem;
            color: #7f8c8d;
            margin-bottom: 5px;
        }
        
        .indicator-value {
            font-size: 1.3rem;
            font-weight: bold;
            color: #2c3e50;
        }
        
        .status {
            padding: 10px;
            border-radius: 8px;
            margin: 10px 0;
            text-align: center;
            font-weight: bold;
        }
        
        .status-connected {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status-disconnected {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .timestamp {
            color: #7f8c8d;
            font-size: 0.9rem;
            text-align: center;
            margin-top: 10px;
        }
        
        .bb-position {
            padding: 8px 12px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: bold;
            margin: 10px auto;
            display: inline-block;
        }
        
        .bb-upper { background: #ff6b6b; color: white; }
        .bb-upper-half { background: #feca57; color: white; }
        .bb-lower-half { background: #48cae4; color: white; }
        .bb-lower { background: #06ffa5; color: black; }
        
        .signals-history {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .signal-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            margin: 5px 0;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }
        
        .signal-item.buy { border-left-color: #27ae60; }
        .signal-item.sell { border-left-color: #e74c3c; }
        
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 1.8rem;
            }
            
            .price-display {
                font-size: 2rem;
            }
            
            .signal-display {
                font-size: 1.5rem;
                padding: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>🚀 Live Trading Dashboard</h1>
            <p class="subtitle">Bollinger Bands + MACD Strategy (Realistic1 - Winner Configuration)</p>
            <div id="connection-status" class="status status-disconnected">
                Connecting...
            </div>
        </div>
        
        <div class="grid">
            <!-- Current Signal -->
            <div class="card">
                <h2>📡 Current Signal</h2>
                <div id="current-signal" class="signal-display signal-neutral">
                    NEUTRAL
                </div>
                <div id="signal-timestamp" class="timestamp">
                    Waiting for data...
                </div>
            </div>
            
            <!-- Current Price -->
            <div class="card">
                <h2>💰 BTC/USDT Price</h2>
                <div id="current-price" class="price-display">
                    $---.--
                </div>
                <div id="price-change" class="price-change">
                    ---%
                </div>
                <div id="bb-position" class="bb-position">
                    Position: Unknown
                </div>
            </div>
            
            <!-- Technical Indicators -->
            <div class="card">
                <h2>📊 Technical Indicators</h2>
                <div class="indicator-grid">
                    <div class="indicator">
                        <div class="indicator-label">RSI (14)</div>
                        <div id="rsi-value" class="indicator-value">--</div>
                    </div>
                    <div class="indicator">
                        <div class="indicator-label">MACD</div>
                        <div id="macd-value" class="indicator-value">--</div>
                    </div>
                    <div class="indicator">
                        <div class="indicator-label">BB Lower</div>
                        <div id="bb-lower" class="indicator-value">--</div>
                    </div>
                    <div class="indicator">
                        <div class="indicator-label">BB Upper</div>
                        <div id="bb-upper" class="indicator-value">--</div>
                    </div>
                </div>
                <div id="indicators-timestamp" class="timestamp">
                    Indicators updated: Waiting for data...
                </div>
            </div>
            
            <!-- Signal History -->
            <div class="card">
                <h2>📈 Recent Signals</h2>
                <div id="signals-history" class="signals-history">
                    No signals yet...
                </div>
            </div>
        </div>
    </div>
    
    <script>
        class TradingDashboard {
            constructor() {
                this.ws = null;
                this.lastPrice = null;
                this.reconnectDelay = 1000;
                this.maxReconnectDelay = 30000;
                this.signalHistory = [];
                this.init();
            }
            
            init() {
                this.connectWebSocket();
                this.updateConnectionStatus('connecting');
            }
            
            connectWebSocket() {
                const wsUrl = `ws://${window.location.host}/ws`;
                this.ws = new WebSocket(wsUrl);
                
                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.updateConnectionStatus('connected');
                    this.reconnectDelay = 1000;
                };
                
                this.ws.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        this.handleMessage(message);
                    } catch (error) {
                        console.error('Error parsing WebSocket message:', error);
                    }
                };
                
                this.ws.onclose = () => {
                    console.log('WebSocket disconnected');
                    this.updateConnectionStatus('disconnected');
                    this.scheduleReconnect();
                };
                
                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                };
            }
            
            scheduleReconnect() {
                setTimeout(() => {
                    this.connectWebSocket();
                    this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxReconnectDelay);
                }, this.reconnectDelay);
            }
            
            handleMessage(message) {
                switch (message.type) {
                    case 'initial':
                    case 'market':
                        this.updateMarketData(message.data);
                        break;
                    case 'signal':
                        this.updateSignal(message.data);
                        this.addSignalToHistory(message.data);
                        break;
                    case 'price_update':
                        this.updateLivePrice(message.data);
                        break;
                }
            }
            
            updateConnectionStatus(status) {
                const statusElement = document.getElementById('connection-status');
                if (status === 'connected') {
                    statusElement.className = 'status status-connected';
                    statusElement.textContent = '✅ Connected - Live Data';
                } else {
                    statusElement.className = 'status status-disconnected';
                    statusElement.textContent = status === 'connecting' ? '🔄 Connecting...' : '❌ Disconnected';
                }
            }
            
            updateMarketData(data) {
                if (!data || !data.price) return;
                
                // Update price
                const priceElement = document.getElementById('current-price');
                const currentPrice = parseFloat(data.price);
                priceElement.textContent = `$${currentPrice.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                
                // Update price change color
                const priceChangeElement = document.getElementById('price-change');
                if (this.lastPrice !== null) {
                    const change = currentPrice - this.lastPrice;
                    const changePercent = (change / this.lastPrice) * 100;
                    priceChangeElement.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)} (${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%)`;
                    priceChangeElement.className = change >= 0 ? 'price-change price-up' : 'price-change price-down';
                }
                this.lastPrice = currentPrice;
                
                // Update indicators
                if (data.indicators) {
                    const rsiElement = document.getElementById('rsi-value');
                    const macdElement = document.getElementById('macd-value');
                    const bbLowerElement = document.getElementById('bb-lower');
                    const bbUpperElement = document.getElementById('bb-upper');
                    
                    if (data.indicators.rsi) {
                        rsiElement.textContent = data.indicators.rsi.toFixed(1);
                    }
                    if (data.indicators.macd) {
                        macdElement.textContent = data.indicators.macd.toFixed(4);
                    }
                    if (data.indicators.bb_lower) {
                        bbLowerElement.textContent = data.indicators.bb_lower.toFixed(2);
                    }
                    if (data.indicators.bb_upper) {
                        bbUpperElement.textContent = data.indicators.bb_upper.toFixed(2);
                    }
                }
                
                // Update BB position
                if (data.bb_position) {
                    const bbPositionElement = document.getElementById('bb-position');
                    bbPositionElement.textContent = `Position: ${data.bb_position.toUpperCase()}`;
                    bbPositionElement.className = `bb-position bb-${data.bb_position}`;
                }
                
                // Update signal
                if (data.current_signal) {
                    this.updateSignalDisplay(data.current_signal);
                }
                
                // Update signal history if provided (for initial data)
                if (data.signal_history && Array.isArray(data.signal_history)) {
                    this.populateSignalHistory(data.signal_history);
                }
                
                // Update timestamp
                if (data.timestamp) {
                    document.getElementById('signal-timestamp').textContent = 
                        `Updated: ${new Date(data.timestamp).toLocaleString()}`;
                    
                    // Update indicator timestamp if indicators were updated
                    if (data.indicators) {
                        document.getElementById('indicators-timestamp').textContent = 
                            `Indicators updated: ${new Date(data.timestamp).toLocaleString()}`;
                    }
                }
            }
            
            updateLivePrice(data) {
                if (!data || !data.price) return;
                
                // Update price display with live data
                const priceElement = document.getElementById('current-price');
                const currentPrice = parseFloat(data.price);
                priceElement.textContent = `$${currentPrice.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                
                // Update price change with animation
                const priceChangeElement = document.getElementById('price-change');
                if (this.lastPrice !== null) {
                    const change = currentPrice - this.lastPrice;
                    const changePercent = (change / this.lastPrice) * 100;
                    priceChangeElement.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)} (${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%)`;
                    priceChangeElement.className = change >= 0 ? 'price-change price-up' : 'price-change price-down';
                    
                    // Add flash animation for price changes
                    priceElement.style.animation = 'none';
                    setTimeout(() => {
                        priceElement.style.animation = change >= 0 ? 'flashGreen 0.5s' : 'flashRed 0.5s';
                    }, 10);
                }
                this.lastPrice = currentPrice;
                
                // Update indicators if available
                if (data.indicators) {
                    const rsiElement = document.getElementById('rsi-value');
                    const macdElement = document.getElementById('macd-value');
                    const bbLowerElement = document.getElementById('bb-lower');
                    const bbUpperElement = document.getElementById('bb-upper');
                    
                    if (data.indicators.rsi) {
                        rsiElement.textContent = data.indicators.rsi.toFixed(1);
                        rsiElement.className = 'indicator-value ' + (data.indicators.rsi > 70 ? 'overbought' : data.indicators.rsi < 30 ? 'oversold' : 'neutral');
                    }
                    if (data.indicators.macd) {
                        macdElement.textContent = data.indicators.macd.toFixed(4);
                    }
                    if (data.indicators.bb_lower) {
                        bbLowerElement.textContent = `$${data.indicators.bb_lower.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                    }
                    if (data.indicators.bb_upper) {
                        bbUpperElement.textContent = `$${data.indicators.bb_upper.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                    }
                }
                
                // Update current signal if available
                if (data.current_signal) {
                    this.updateSignalDisplay(data.current_signal);
                }
                
                // Update timestamp for price updates
                document.getElementById('signal-timestamp').textContent = 
                    `Price updated: ${new Date().toLocaleString()}`;
                
                // Update indicator timestamp only if indicators were recalculated
                if (data.indicator_updated && data.timestamp) {
                    document.getElementById('indicators-timestamp').textContent = 
                        `Indicators updated: ${new Date(data.timestamp).toLocaleString()}`;
                }
            }
            
            updateSignal(signalData) {
                this.updateSignalDisplay(signalData.signal);
                
                // Show notification for new signals
                if (signalData.signal !== 'NEUTRAL') {
                    this.showNotification(signalData);
                }
            }
            
            updateSignalDisplay(signal) {
                const signalElement = document.getElementById('current-signal');
                signalElement.textContent = signal;
                signalElement.className = `signal-display signal-${signal.toLowerCase()}`;
            }
            
            addSignalToHistory(signalData) {
                this.signalHistory.unshift(signalData);
                if (this.signalHistory.length > 10) {
                    this.signalHistory = this.signalHistory.slice(0, 10);
                }
                this.updateSignalHistory();
            }
            
            populateSignalHistory(signalHistory) {
                // Replace current history with the provided one (for initial load)
                this.signalHistory = signalHistory.slice(0, 10); // Keep only last 10
                this.updateSignalHistory();
            }
            
            updateSignalHistory() {
                const historyElement = document.getElementById('signals-history');
                
                if (this.signalHistory.length === 0) {
                    historyElement.innerHTML = 'No signals yet...';
                    return;
                }
                
                const historyHtml = this.signalHistory.map(signal => {
                    const time = new Date(signal.timestamp).toLocaleTimeString();
                    const price = parseFloat(signal.price).toFixed(2);
                    return `
                        <div class="signal-item ${signal.signal.toLowerCase()}">
                            <div>
                                <strong>${signal.signal}</strong> at $${price}
                                <br><small>RSI: ${signal.rsi ? signal.rsi.toFixed(1) : 'N/A'}</small>
                            </div>
                            <div>${time}</div>
                        </div>
                    `;
                }).join('');
                
                historyElement.innerHTML = historyHtml;
            }
            
            showNotification(signalData) {
                // Browser notification (if permission granted)
                if (Notification.permission === 'granted') {
                    new Notification(`Trading Signal: ${signalData.signal}`, {
                        body: `BTC/USDT at $${parseFloat(signalData.price).toFixed(2)}`,
                        icon: signalData.signal === 'BUY' ? '🟢' : '🔴'
                    });
                }
            }
        }
        
        // Request notification permission
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
        
        // Initialize dashboard
        const dashboard = new TradingDashboard();
    </script>
</body>
</html>
        '''
    
    async def start(self):
        """Start the trading dashboard server"""
        try:
            logger.info("Starting live signal generator...")
            
            # Add callbacks to signal generator
            self.signal_generator.add_signal_callback(self._on_signal_update)
            
            # Initialize signal generator in background
            asyncio.create_task(self.signal_generator.initialize())
            
            # Start web server
            logger.info(f"Starting web server on http://localhost:{self.port}")
            config = uvicorn.Config(self.app, host="0.0.0.0", port=self.port, log_level="info")
            server = uvicorn.Server(config)
            
            await server.serve()
            
        except Exception as e:
            logger.error(f"Error starting dashboard server: {e}")
            raise
    
    async def stop(self):
        """Stop the server"""
        logger.info("Stopping trading dashboard server...")
        await self.signal_generator.stop()


async def main():
    """Main entry point"""
    server = TradingDashboardServer(symbol="btcusdt", interval="5m", port=8000)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())