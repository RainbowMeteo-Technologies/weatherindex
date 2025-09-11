import aiohttp
import asyncio
import logging


class Http:
    @staticmethod
    async def get(url: str, headers: dict = {}, retry_count: int = 5) -> bytes | None:
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
        data : bytes | None
            The data from the url
        """

        async with aiohttp.ClientSession(headers=headers) as session:
            return await Http.get_with_session(url=url,
                                               session=session,
                                               headers=headers,
                                               retry_count=retry_count)

    @staticmethod
    async def get_with_session(url: str,
                               session: aiohttp.ClientSession,
                               headers: dict = {},
                               retry_count: int = 5) -> bytes | None:
        """
        Get the data from the url using provided session object

        Parameters
        ----------
        url : str
            The url to get the data from
        session : aiohttp.ClientSession
            Session object to use for performing requests
        headers : dict
            The headers to send to the url
        retry_count : int
            The number of retries to get the data

        Returns
        -------
        data : bytes | None
            The data from the url
        """

        remain_retries = retry_count
        response = None
        while remain_retries > 0:
            try:
                response = await session.get(url, headers=headers)

                if response.status == 200:
                    return await response.read()

            except BaseException as ex:
                logging.warning(f"Wasn't able to download `{url}`")
                if remain_retries == 1:
                    logging.exception(ex)

            # Wait for the next try
            if remain_retries > 0:
                logging.info(f"Waiting for 1 second before retrying to download `{url}`")

                await asyncio.sleep(1)
                remain_retries -= 1

        return None
