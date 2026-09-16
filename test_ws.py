import asyncio
import websockets

async def test_ws():
    try:
        async with websockets.connect('ws://localhost:8000/ws/live', open_timeout=5) as ws:
            await ws.send('{"type": "ping"}')
            resp = await asyncio.wait_for(ws.recv(), timeout=3)
            print('WS_OK:', resp)
    except Exception as e:
        print(f'WS_FAIL: {e}')

asyncio.run(test_ws())