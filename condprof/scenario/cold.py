import asyncio


async def cold(session, args):
    # nothing is done, we just settle here for 30 seconds
    await asyncio.sleep(30)
    return {}
