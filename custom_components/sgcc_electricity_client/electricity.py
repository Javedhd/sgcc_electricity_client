import json
import asyncio
import traceback

from .utils.logger import LOGGER
from .const import CONFIG_NAME
from .utils.store import async_save_to_store

USER_LIST_URL = '{addr}/v1/electricity/user_list'
BALANCE_URL = '{addr}/v1/electricity/balance/{user_id}'
DAILYS_URL = '{addr}/v1/electricity/dailys/{user_id}'
LATEST_MONTH_URL = '{addr}/v1/electricity/latest_month/{user_id}'
THIS_YEAR_URL = '{addr}/v1/electricity/this_year/{user_id}'

class Electricity:
    def __init__(self, hass, session, addr, data=None):
        self._hass = hass
        self._session = session
        self._addr = addr
        self._user_list = []
        self._data = {} if data == None else data

    def get_user_list(self):
        return self._user_list
    
    def get_data(self):
        return self._data
    
    async def async_get_user_list(self):
        r = await self._session.get(USER_LIST_URL.format(addr=self._addr), timeout=10)
        result = []
        if r.status == 200:
            result = json.loads(await r.read())
        self._user_list = result
        return result

    async def async_get_balance(self, user_id):
        try:
            r = await self._session.get(BALANCE_URL.format(addr=self._addr, user_id=user_id), timeout=10)
            if r.status == 200:
                result = json.loads(await r.read())
                self._data[user_id]["balance"] = result.get('balance', 0)
                self._data[user_id]["refresh_time"] = result.get('updateTime', 'unknown')
            else:
                LOGGER.warning(f"Balance API failed for {user_id}: HTTP {r.status}")
                self._data[user_id]["balance"] = None
                self._data[user_id]["refresh_time"] = 'unavailable'
        except Exception as e:
            LOGGER.error(f"Balance API error for {user_id}: {e}")
            self._data[user_id]["balance"] = None
            self._data[user_id]["refresh_time"] = 'error'

    async def async_get_dailys(self, user_id):
        try:
            r = await self._session.get(DAILYS_URL.format(addr=self._addr, user_id=user_id), timeout=10)
            if r.status == 200:
                result = json.loads(await r.read())
                self._data[user_id]["dailys"] = result if result else []
            else:
                LOGGER.warning(f"Dailys API failed for {user_id}: HTTP {r.status}")
                self._data[user_id]["dailys"] = []
        except Exception as e:
            LOGGER.error(f"Dailys API error for {user_id}: {e}")
            self._data[user_id]["dailys"] = []

    async def async_get_latest_month(self, user_id):
        try:
            r = await self._session.get(LATEST_MONTH_URL.format(addr=self._addr, user_id=user_id), timeout=10)
            if r.status == 200:
                result = json.loads(await r.read())
                self._data[user_id]["last_month_ele_num"] = result.get("usage", 0)
                self._data[user_id]["last_month_ele_cost"] = result.get("charge", 0)
            else:
                LOGGER.warning(f"Latest month API failed for {user_id}: HTTP {r.status}")
                self._data[user_id]["last_month_ele_num"] = None
                self._data[user_id]["last_month_ele_cost"] = None
        except Exception as e:
            LOGGER.error(f"Latest month API error for {user_id}: {e}")
            self._data[user_id]["last_month_ele_num"] = None
            self._data[user_id]["last_month_ele_cost"] = None
    
    async def async_get_this_year(self, user_id):
        try:
            r = await self._session.get(THIS_YEAR_URL.format(addr=self._addr, user_id=user_id), timeout=10)
            if r.status == 200:
                result = json.loads(await r.read())
                self._data[user_id]["year_ele_num"] = result.get("usage", 0)
                self._data[user_id]["year_ele_cost"] = result.get("charge", 0)
            else:
                LOGGER.warning(f"This year API failed for {user_id}: HTTP {r.status}")
                self._data[user_id]["year_ele_num"] = None
                self._data[user_id]["year_ele_cost"] = None
        except Exception as e:
            LOGGER.error(f"This year API error for {user_id}: {e}")
            self._data[user_id]["year_ele_num"] = None
            self._data[user_id]["year_ele_cost"] = None
    
    async def async_get_data(self):
        try:
            user_list = await self.async_get_user_list()
            LOGGER.debug(f"user_list: {user_list}")

            for user_id in user_list:
                if user_id not in self._data:
                    # 初始化完整的数据结构
                    self._data[user_id] = {
                        "balance": None,
                        "year_ele_num": None,
                        "year_ele_cost": None,
                        "last_month_ele_num": None,
                        "last_month_ele_cost": None,
                        "refresh_time": None,
                        "dailys": []
                    }
                
                # 分别处理每个API调用，避免一个失败影响全部
                try:
                    await self.async_get_balance(user_id)
                except Exception as e:
                    LOGGER.error(f"Failed to get balance for {user_id}: {e}")
                    
                try:
                    await self.async_get_dailys(user_id)
                except Exception as e:
                    LOGGER.error(f"Failed to get dailys for {user_id}: {e}")
                    
                try:
                    await self.async_get_latest_month(user_id)
                except Exception as e:
                    LOGGER.error(f"Failed to get latest month for {user_id}: {e}")
                    
                try:
                    await self.async_get_this_year(user_id)
                except Exception as e:
                    LOGGER.error(f"Failed to get this year for {user_id}: {e}")
                    
            LOGGER.debug(f"Final data structure: {json.dumps(self._data)}")
            await async_save_to_store(self._hass,CONFIG_NAME,self._data)
        except Exception as err:
            traceback.print_exc()
            LOGGER.error(f"get data error :{err}")
        return self._data

    
