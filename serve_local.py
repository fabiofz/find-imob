"""Proxy local: redireciona HTTP para HTTPS e encaminha TLS ao Streamlit."""
import asyncio
import signal
import sys

ROOT = "findimob.local"
PUBLIC_PORT = 8501
APP_HOST = "127.0.0.1"
APP_PORT = 8502
MAX_HEADER_LINE = 16 * 1024


async def _pipe(source, destination):
    try:
        while True:
            chunk = await source.read(65536)
            if not chunk:
                break
            destination.write(chunk)
            await destination.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        try:
            destination.write_eof()
        except (AttributeError, OSError, RuntimeError):
            pass


async def _proxy_tls(reader, writer, first_byte):
    try:
        app_reader, app_writer = await asyncio.open_connection(APP_HOST, APP_PORT)
        app_writer.write(first_byte)
        await app_writer.drain()
        tasks = {
            asyncio.create_task(_pipe(reader, app_writer)),
            asyncio.create_task(_pipe(app_reader, writer)),
        }
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*done, *pending, return_exceptions=True)
        app_writer.close()
        await app_writer.wait_closed()
    except (ConnectionError, OSError):
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass


async def _redirect_http(reader, writer, first_byte):
    try:
        request_line = first_byte + await reader.readline()
        parts = request_line.decode("latin-1", errors="replace").strip().split()
        path = parts[1] if len(parts) >= 2 and parts[1].startswith("/") else "/"
        if "\r" in path or "\n" in path:
            path = "/"
        total = 0
        while total < 65536:
            line = await reader.readline()
            total += len(line)
            if not line or line in (b"\r\n", b"\n"):
                break
        response = (
            f"HTTP/1.1 308 Permanent Redirect\r\n"
            f"Location: https://{ROOT}:{PUBLIC_PORT}{path}\r\n"
            "Cache-Control: no-store\r\n"
            "Connection: close\r\n"
            "Content-Length: 0\r\n\r\n"
        )
        writer.write(response.encode("ascii", errors="ignore"))
        await writer.drain()
    except (ConnectionError, OSError, asyncio.LimitOverrunError):
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass


async def handle_client(reader, writer):
    try:
        first_byte = await reader.readexactly(1)
    except (ConnectionError, asyncio.IncompleteReadError):
        writer.close()
        return
    if first_byte == b"\x16":
        await _proxy_tls(reader, writer, first_byte)
    else:
        await _redirect_http(reader, writer, first_byte)


async def main():
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.address", APP_HOST, "--server.port", str(APP_PORT),
    )
    try:
        for _ in range(100):
            if process.returncode is not None:
                raise RuntimeError("O Streamlit terminou antes de abrir a porta TLS.")
            try:
                _, probe = await asyncio.wait_for(
                    asyncio.open_connection(APP_HOST, APP_PORT), timeout=0.3
                )
                probe.close()
                await probe.wait_closed()
                break
            except (OSError, asyncio.TimeoutError):
                await asyncio.sleep(0.1)
        else:
            raise RuntimeError("O Streamlit nao abriu a porta TLS no tempo esperado.")

        server = await asyncio.start_server(handle_client, "0.0.0.0", PUBLIC_PORT)
        print(
            f"Find Imob ativo em https://{ROOT}:{PUBLIC_PORT} (HTTP redireciona para HTTPS)",
            flush=True,
        )
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        async with server:
            stopped = asyncio.create_task(stop.wait())
            exited = asyncio.create_task(process.wait())
            done, pending = await asyncio.wait(
                (stopped, exited), return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()


if __name__ == "__main__":
    asyncio.run(main())
