import aiohttp
import asyncio
import logging
import typing


class Http:
    @staticmethod
    async def get(url: str, headers: dict = {}, retry_count: int = 5) -> typing.Optional[typing.Any]:
        """
        Get the data from the url

        Parameters
        ----------
        url : str
            The url to get the data from
        headers : dict
            The headers to send to the url
        retry_count : int
            The number of retries to get the data

        Returns
        -------
        data : typing.Optional[typing.Any]
            The data from the url
        """
        remain_retries = retry_count
        while remain_retries > 0:
            # Download the data
            async with aiohttp.ClientSession(headers=headers) as session:
                try:
                    response = await session.get(url)
                except Exception as ex:
                    logging.warning(f"Wasn't able to download `{url}`")
                    if remain_retries == 1:
                        logging.exception(ex)

                # Check if the data is downloaded
                if response.status == 200:
                    return await response.read()

            # Wait for the next try
            if remain_retries > 0:
                logging.info(f"Waiting for 1 second before retrying to download `{url}`")

                await asyncio.sleep(1)
                remain_retries -= 1

        return None
