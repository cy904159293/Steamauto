import os
import time

from requests.exceptions import ProxyError
from steampy.exceptions import InvalidCredentials

import uuyoupinapi

from utils.logger import handle_caught_exception
from utils.static import UU_TOKEN_FILE_PATH
from utils.tools import get_encoding, exit_code


class UUAutoAcceptOffer:
    def __init__(self, logger, steam_client, config):
        self.logger = logger
        self.steam_client = steam_client
        self.config = config

    def init(self) -> bool:
        if not os.path.exists(UU_TOKEN_FILE_PATH):
            with open(UU_TOKEN_FILE_PATH, "w", encoding="utf-8") as f:
                f.write("")
            return True
        return False

    def exec(self):
        uuyoupin = None
        with open(UU_TOKEN_FILE_PATH, "r", encoding=get_encoding(UU_TOKEN_FILE_PATH)) as f:
            try:
                uuyoupin = uuyoupinapi.UUAccount(f.read())
                self.logger.info("[UUAutoAcceptOffer] 悠悠有品登录完成, 用户名: " + uuyoupin.get_user_nickname())
                uuyoupin.send_device_info()
            except KeyError as e:
                handle_caught_exception(e)
                self.logger.error("[UUAutoAcceptOffer] 悠悠有品登录失败! 请检查token是否正确! ")
                self.logger.error("[UUAutoAcceptOffer] 由于登录失败，插件将自动退出")
                exit_code.set(1)
                return 1
        ignored_offer = []
        interval = self.config["uu_auto_accept_offer"]["interval"]
        if uuyoupin is not None:
            while True:
                try:
                    uuyoupin.send_device_info()
                    self.logger.info("[UUAutoAcceptOffer] 正在检查悠悠有品待发货信息...")
                    uu_wait_deliver_list = uuyoupin.get_wait_deliver_list()
                    len_uu_wait_deliver_list = len(uu_wait_deliver_list)
                    self.logger.info("[UUAutoAcceptOffer] " + str(len_uu_wait_deliver_list) + "个悠悠有品待发货订单")
                    if len(uu_wait_deliver_list) != 0:
                        for item in uu_wait_deliver_list:
                            self.logger.info(
                                f"[UUAutoAcceptOffer] 正在接受悠悠有品待发货报价, 商品名: {item['item_name']}, " f"报价ID: {item['offer_id']}"
                            )
                            if item["offer_id"] is None:
                                self.logger.warning("[UUAutoAcceptOffer] 此订单为需要手动发货的订单, 无法处理, 跳过此订单! ")
                            elif item["offer_id"] not in ignored_offer:
                                try:
                                    self.steam_client.accept_trade_offer(str(item["offer_id"]))
                                except Exception as e:
                                    handle_caught_exception(e)
                                    self.logger.error("[UUAutoAcceptOffer] Steam网络异常, 暂时无法接受报价, 请稍后再试! ")
                                ignored_offer.append(item["offer_id"])
                                self.logger.info("[UUAutoAcceptOffer] 接受完成! 已经将此交易报价加入忽略名单! ")
                            else:
                                self.logger.info("[UUAutoAcceptOffer] 此交易报价已经在忽略名单中, 跳过此报价! ")
                            if uu_wait_deliver_list.index(item) != len_uu_wait_deliver_list - 1:
                                self.logger.info("[UUAutoAcceptOffer] 为了避免频繁访问Steam接口, 等待5秒后继续...")
                                time.sleep(5)
                except ProxyError:
                    self.logger.error('代理异常, 本软件可不需要代理或任何VPN')
                    self.logger.error('可以尝试关闭代理或VPN后重启软件')
                except (ConnectionError, ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError):
                    self.logger.error('网络异常, 请检查网络连接')
                    self.logger.error('这个错误可能是由于代理或VPN引起的, 本软件可无需代理或任何VPN')
                    self.logger.error('如果你正在使用代理或VPN, 请尝试关闭后重启软件')
                    self.logger.error('如果你没有使用代理或VPN, 请检查网络连接')
                except InvalidCredentials as e:
                    self.logger.error('mafile有问题, 请检查mafile是否正确(尤其是identity_secret)')
                    self.logger.error(str(e))
                except Exception as e:
                    self.logger.error(e, exc_info=True)
                    self.logger.info("[UUAutoAcceptOffer] 出现未知错误, 稍后再试! ")
                    try:
                        uuyoupin.get_user_nickname()
                    except KeyError as e:
                        handle_caught_exception(e)
                        self.logger.error("[UUAutoAcceptOffer] 检测到悠悠有品登录已经失效,请重新登录")
                        self.logger.error("[UUAutoAcceptOffer] 由于登录失败，插件将自动退出")
                        exit_code.set(1)
                        return 1
                self.logger.info("[UUAutoAcceptOffer] 将在{0}秒后再次检查待发货订单信息!".format(str(interval)))
                time.sleep(interval)
