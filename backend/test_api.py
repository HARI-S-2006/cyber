from streaming.stream_manager import create_app, RedisStreamManager, ThreatAggregator, StreamConfig
import asyncio
import sys
from waitress import serve

PORT = 9999

async def create_app_async(port=9999):
    config = StreamConfig()
    stream_manager = RedisStreamManager(config)
    await stream_manager.connect()
    print('Redis connected!')
    aggregator = ThreatAggregator()
    app = create_app(stream_manager, aggregator)
    print('App created!')
    return app

# Create app at module level
app = asyncio.run(create_app_async(9999))
print('App created for port 9999')

if __name__ == "__main__":
    print(f'Starting server on http://127.0.0.1:9999...')
    serve(app, host='127.0.0.1', port=9999)