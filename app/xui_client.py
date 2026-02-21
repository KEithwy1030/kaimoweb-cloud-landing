"""
3X-UI API客户端模块
用于与3X-UI面板进行交互，管理用户订阅和流量统计
"""
import requests
import uuid
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging
import json

from app.config import settings


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class XuiClient:
    """
    3X-UI面板API客户端
    提供登录、创建用户、获取流量统计等功能
    """

    def __init__(self):
        self.base_url = settings.XUI_BASE_URL  # 不包含 /panel
        self.panel_path = settings.XUI_PANEL_PATH  # /panel
        self.username = settings.XUI_USERNAME
        self.password = settings.XUI_PASSWORD
        self.session = None
        self.cookie = None
        self._session_obj = requests.Session()

    def login(self) -> bool:
        """
        登录3X-UI面板获取会话
        :return: 登录是否成功
        """
        # 3X-UI使用 /login 端点（不是/panel/login）
        login_url = f"{self.base_url}/login"
        try:
            # 使用表单格式登录
            response = self._session_obj.post(
                login_url,
                data={
                    "username": self.username,
                    "password": self.password
                },
                timeout=10,
                allow_redirects=True
            )

            # 检查登录是否成功（会设置 3x-ui cookie）
            if "3x-ui" in response.cookies:
                self.cookie = response.cookies
                self.session = response.cookies.get("3x-ui")
                logger.info(f"3X-UI登录成功 (status: {response.status_code})")
                return True
            else:
                logger.error(f"3X-UI登录失败: 未获取到session cookie, status: {response.status_code}")
                logger.debug(f"响应内容: {response.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"3X-UI登录异常: {str(e)}")
            return False

    def _ensure_logged_in(self) -> bool:
        """
        确保已登录
        :return: 是否已登录
        """
        if not self.session:
            return self.login()
        return True

    def _api_call(self, endpoint: str, method: str = "GET", data: dict = None) -> Optional[dict]:
        """
        通用API调用方法
        :param endpoint: API端点 (如 /inbounds/list, /inbounds/update)
        :param method: HTTP方法
        :param data: 请求数据
        :return: 响应JSON，失败返回None
        """
        if not self._ensure_logged_in():
            return None

        # API调用使用 /panel/api/{endpoint}
        url = f"{self.base_url}{self.panel_path}/api{endpoint}"
        headers = {"Accept": "application/json"}

        try:
            if method.upper() == "GET":
                response = self._session_obj.get(
                    url,
                    headers=headers,
                    cookies=self.cookie,
                    timeout=10
                )
            elif method.upper() == "POST":
                response = self._session_obj.post(
                    url,
                    json=data,
                    headers=headers,
                    cookies=self.cookie,
                    timeout=10
                )
            elif method.upper() == "PUT":
                response = self._session_obj.put(
                    url,
                    json=data,
                    headers=headers,
                    cookies=self.cookie,
                    timeout=10
                )
            elif method.upper() == "DELETE":
                response = self._session_obj.delete(
                    url,
                    json=data,
                    headers=headers,
                    cookies=self.cookie,
                    timeout=10
                )
            else:
                logger.error(f"不支持的HTTP方法: {method}")
                return None

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API调用失败: {endpoint}, 状态码: {response.status_code}, 响应: {response.text[:200]}")
                return None

        except Exception as e:
            logger.error(f"API调用异常: {endpoint}, 错误: {str(e)}")
            return None

    def get_inbounds(self) -> Optional[List[Dict]]:
        """
        获取所有入站配置
        :return: 入站列表，失败返回None
        """
        result = self._api_call("/inbounds/list", "GET")
        if result and result.get("success"):
            return result.get("obj", [])
        return None

    def get_inbound(self, inbound_id: int) -> Optional[Dict]:
        """
        获取指定入站配置
        :param inbound_id: 入站ID
        :return: 入站配置，失败返回None
        """
        result = self._api_call(f"/inbounds/get/{inbound_id}", "GET")
        if result and result.get("success"):
            return result.get("obj")
        return None

    def add_client(
        self,
        inbound_id: int,
        email: str,
        flow: str = "",
        traffic_gb: int = 130,
        expiry_days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        在指定入站下添加客户端
        :param inbound_id: 入站ID
        :param email: 用户邮箱标识
        :param flow: 流控 (通常为空)
        :param traffic_gb: 流量额度（GB）
        :param expiry_days: 过期天数
        :return: 创建结果，失败返回None
        """
        import json

        # 首先获取现有入站配置
        inbound = self.get_inbound(inbound_id)
        if not inbound:
            logger.error(f"无法获取入站配置: {inbound_id}")
            return None

        # 生成UUID
        client_id = str(uuid.uuid4())

        # 计算过期时间戳
        from datetime import datetime, timedelta
        expiry_time = int((datetime.now() + timedelta(days=expiry_days)).timestamp())

        # 将GB转换为字节
        traffic_bytes = traffic_gb * 1024 * 1024 * 1024

        # 构造客户端配置 (根据3X-UI API规范)
        client_settings = {
            "id": client_id,
            "email": email,
            "flow": flow,
            "limitIp": 3,  # 限制3个IP
            "totalGB": traffic_bytes,
            "expiryTime": expiry_time * 1000,  # 毫秒时间戳
            "enable": True,
            "tgId": "",
            "subId": ""
        }

        # 获取现有客户端列表 - 注意：settings是JSON字符串，需要解析
        settings_str = inbound.get("settings", "{}")
        try:
            settings_data = json.loads(settings_str) if isinstance(settings_str, str) else settings_str
        except:
            settings_data = {}

        clients = settings_data.get("clients", [])

        # 添加新客户端
        clients.append(client_settings)
        settings_data["clients"] = clients

        # 更新入站配置 - 将settings转换回JSON字符串
        update_data = {
            "id": inbound_id,
            "up": inbound.get("up", 0),
            "down": inbound.get("down", 0),
            "total": inbound.get("total", 0),
            "remark": inbound.get("remark", ""),
            "enable": inbound.get("enable", True),
            "expiryTime": inbound.get("expiryTime", 0),
            "trafficReset": inbound.get("trafficReset", "never"),
            "listen": inbound.get("listen", ""),
            "port": inbound.get("port", 443),
            "protocol": inbound.get("protocol", "vless"),
            "settings": json.dumps(settings_data),
            "decryption": inbound.get("decryption", "none"),
            "streamSettings": inbound.get("streamSettings", ""),
            "tag": inbound.get("tag", ""),
            "sniffing": inbound.get("sniffing", "")
        }

        # 使用 /inbounds/update/{id} 端点更新入站配置
        # 注意：需要传入完整的入站配置，包括新的客户端列表
        result = self._api_call(f"/inbounds/update/{inbound_id}", "POST", update_data)

        if result and result.get("success"):
            logger.info(f"3X-UI添加客户端成功: {email}, UUID: {client_id}")
            return {
                "email": email,
                "uuid": client_id,
                "total_gb": traffic_gb,
                "total_bytes": traffic_bytes,
                "expiry_time": expiry_time
            }
        else:
            logger.error(f"3X-UI添加客户端失败: {result.get('msg', '未知错误') if result else '无响应'}")
            return None

    def delete_client(self, inbound_id: int, email: str) -> bool:
        """
        删除指定入站下的客户端
        :param inbound_id: 入站ID
        :param email: 客户端邮箱标识
        :return: 删除是否成功
        """
        # 使用 delClientByEmail 端点删除客户端
        result = self._api_call(f"/inbounds/{inbound_id}/delClientByEmail/{email}", "POST")

        if result and result.get("success"):
            logger.info(f"3X-UI删除客户端成功: {email}")
            return True
        else:
            logger.error(f"3X-UI删除客户端失败: {result.get('msg', '未知错误') if result else '无响应'}")
            return False

    def get_client_traffic(self, inbound_id: int, email: str) -> Optional[Dict[str, Any]]:
        """
        获取指定客户端的流量统计
        :param inbound_id: 入站ID
        :param email: 客户端邮箱标识
        :return: 流量统计信息，失败返回None
        """
        inbound = self.get_inbound(inbound_id)
        if not inbound:
            return None

        settings_data = inbound.get("settings", {})
        clients = settings_data.get("clients", [])

        for client in clients:
            if client.get("email") == email:
                # 从client_stats获取流量数据
                client_stats = inbound.get("client_stats", [])
                for stat in client_stats:
                    if stat.get("email") == email:
                        return {
                            "email": email,
                            "upload_bytes": stat.get("up", 0),
                            "download_bytes": stat.get("down", 0),
                            "total_bytes": stat.get("up", 0) + stat.get("down", 0),
                            "upload_gb": stat.get("up", 0) / (1024**3),
                            "download_gb": stat.get("down", 0) / (1024**3),
                            "total_gb": (stat.get("up", 0) + stat.get("down", 0)) / (1024**3)
                        }

        logger.warning(f"未找到客户端流量信息: {email}")
        return None

    def get_all_clients_traffic(self, inbound_id: int = None) -> List[Dict[str, Any]]:
        """
        获取所有客户端的流量统计
        :param inbound_id: 入站ID，不指定则使用默认配置
        :return: 所有客户端流量信息列表
        """
        if inbound_id is None:
            inbound_id = settings.XUI_INBOUND_ID

        inbound = self.get_inbound(inbound_id)
        if not inbound:
            return []

        settings_data = inbound.get("settings", {})
        clients = settings_data.get("clients", [])
        client_stats = inbound.get("client_stats", [])

        # 创建email到stats的映射
        stats_map = {}
        for stat in client_stats:
            email = stat.get("email", "")
            if email:
                stats_map[email] = stat

        user_traffics = []
        for client in clients:
            email = client.get("email", "")
            if email:
                stat = stats_map.get(email, {})
                user_traffics.append({
                    "email": email,
                    "uuid": client.get("id", ""),
                    "upload_bytes": stat.get("up", 0),
                    "download_bytes": stat.get("down", 0),
                    "total_bytes": stat.get("up", 0) + stat.get("down", 0)
                })

        logger.info(f"获取到 {len(user_traffics)} 个客户端的流量信息")
        return user_traffics

    def generate_subscription_url(self, token: str) -> str:
        """
        生成订阅链接
        :param token: 订阅Token
        :return: 订阅链接
        """
        return f"{settings.SUBSCRIPTION_BASE_URL}{settings.SUBSCRIPTION_PATH}/{token}"

    def generate_vless_url(
        self,
        uuid: str,
        server: str,
        port: int,
        email: str,
        security: str = "none"
    ) -> str:
        """
        生成VLESS连接URL
        :param uuid: 客户端UUID
        :param server: 服务器地址
        :param port: 端口
        :param email: 客户端邮箱（用作备注）
        :param security: 安全类型
        :return: VLESS URL
        """
        return f"vless://{uuid}@{server}:{port}?type=tcp&encryption=none&security={security}#{email}"


    def get_all_users_traffic(self, inbound_id: int = None) -> List[Dict[str, Any]]:
        """
        获取所有用户的流量统计（别名方法，用于兼容scheduler.py）
        :param inbound_id: 入站ID，不指定则使用默认配置
        :return: 所有客户端流量信息列表
        """
        return self.get_all_clients_traffic(inbound_id)


# 创建全局X-ui客户端实例
xui_client = XuiClient()


def get_xui_client() -> XuiClient:
    """获取X-ui客户端实例（依赖注入）"""
    return xui_client
