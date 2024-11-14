import asyncio
import random
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent
from http.server import HTTPServer, SimpleHTTPRequestHandler
import ssl
import threading

async def connect_to_wss(socks5_proxy, user_id):
    user_agent = UserAgent(os=['windows', 'macos', 'linux'], browsers='chrome')
    random_user_agent = user_agent.random
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(f"Device ID: {device_id}")

    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)
            custom_headers = {
                "User-Agent": random_user_agent,
            }

            urilist = ["wss://proxy2.wynd.network:4444/", "wss://proxy2.wynd.network:4650/"]
            uri = random.choice(urilist)
            server_hostname = "proxy2.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)

            async with proxy_connect(uri, proxy=proxy, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    while True:
                        send_message = json.dumps({
                            "id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}
                        })
                        logger.debug(f"Sending ping: {send_message}")
                        await websocket.send(send_message)
                        await asyncio.sleep(5)

                await asyncio.sleep(1)
                asyncio.create_task(send_ping())

                while True:
                    response = await websocket.recv()
                    message = json.loads(response)
                    logger.info(f"Received message: {message}")

                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": custom_headers['User-Agent'],
                                "timestamp": int(time.time()),
                                "device_type": "desktop",
                                "version": "4.28.2",
                            }
                        }
                        logger.debug(f"Sending auth response: {auth_response}")
                        await websocket.send(json.dumps(auth_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(f"Sending pong response: {pong_response}")
                        await websocket.send(json.dumps(pong_response))
        except Exception as e:
            logger.error(f"Error with proxy {socks5_proxy}: {e}")

async def main():
    try:
        with open('user_id.txt', 'r') as f:
            _user_id = f.read().strip()
        if not _user_id:
            print("No user ID found in 'user_id.txt'.")
            return
        print(f"User ID read from file: {_user_id}")
    except FileNotFoundError:
        print("Error: 'user_id.txt' file not found.")
        return

    try:
        with open('local_proxies.txt', 'r') as file:
            local_proxies = file.read().splitlines()
            if not local_proxies:
                print("No proxies found in 'local_proxies.txt'.")
                return
            print(f"Proxies read from file: {local_proxies}")
    except FileNotFoundError:
        print("Error: 'local_proxies.txt' file not found.")
        return

    tasks = [asyncio.ensure_future(connect_to_wss(proxy, _user_id)) for proxy in local_proxies]
    await asyncio.gather(*tasks)

# Basic HTTP server handler for the '/' route
class SimpleHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Hello! The server is running with SSL.")

def start_https_server():
    server_address = ('127.0.0.1', 9000)
    httpd = HTTPServer(server_address, SimpleHandler)
    
    # Wrap the HTTP server socket in SSL using self-signed certificates
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')
    httpd.socket = ssl_context.wrap_socket(httpd.socket, server_side=True)
    
    logger.info("HTTPS server started on https://127.0.0.1:9000")
    httpd.serve_forever()

if __name__ == '__main__':
    # Start HTTPS server in a separate thread to allow asyncio loop to run concurrently
    server_thread = threading.Thread(target=start_https_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Run asyncio event loop
    asyncio.run(main())
