import os
import socket
import configparser
from enums.DBDataTypeEnum import DBDataTypeEnum
from util.shellutil import CommandRunner
from util.taosdbutil import TaosUtil
import subprocess

class InstallTaosDB(object):
    def __init__(self, logger):
        # 日志信息
        self.__version = ""
        self.__logger = logger
        self.__branch = ""
        self.__data_scale = "mid"
        self.__hostname = socket.gethostname()

        self.__commit_id = None
        self.__taosdbHandler = TaosUtil(self.__logger)

        # 初始化读取配置文件实例
        confile = os.path.join(os.path.dirname(__file__), "conf", "config.ini")
        self.__cf = configparser.ConfigParser()
        self.__cf.read(confile, encoding='UTF-8')

        self.__db_install_path = self.__cf.get("machineconfig", "tdengine_path")
        self.__perf_test_path = self.__cf.get("machineconfig", "perf_test_path")

        self.__cmdHandler = CommandRunner(self.__logger)

    def set_branch(self, branch: str = "main"):
        self.__branch = branch

    def get_branch(self):
        return self.__branch

    def set_version(self, version: str):
        self.__version = version

    def get_version(self):
        return self.__version

    def get_commit_id(self):
        stdout = self.__cmdHandler.run_command(path=self.__db_install_path, command="git rev-parse --short @")
        self.__commit_id = stdout
        return self.__commit_id

    def install(self):
        # 安装db
        try:
            self.__logger.info("代码Branch  : [{0}]".format(self.__branch))
            self.__logger.info("本地代码路径 : [{0}]".format(self.__db_install_path))

            # 获取测试机器信息
            cluster_id = "1"
            condition_info = [("cluster_id", cluster_id, DBDataTypeEnum.int), ("valid", "1", DBDataTypeEnum.int)]
            machine_info = self.__taosdbHandler.select(database="perf_test", table="machine_info",
                                                       condition_info=condition_info)

            self.__logger.info("执行机器信息 ->")
            self.__logger.info("[")
            for machine in machine_info:
                self.__logger.info("  HostName: {0}".format(socket.gethostname()))
                self.__logger.info("  HostIP  : {0}".format(machine[2]))
                self.__logger.info("  Leader  : {0}".format(machine[3]))
                self.__logger.info("  CPU     : {0}".format(machine[5]))
                self.__logger.info("  MEM     : {0}".format(machine[6]))
                self.__logger.info("  DISK    : {0}".format(machine[7]))
                self.__logger.info("")
            self.__logger.info("]")

            # 判断DB的源代码本地是否存在，若不存在，git clone到本地
            if not os.path.exists(os.path.join(self.__db_install_path, "build.sh")):
                if os.path.exists(os.path.join(self.__db_install_path)):
                    self.__cmdHandler.run_command(path=self.__perf_test_path,
                                                  command="rm -rf {0}".format(self.__db_install_path))
                self.__cmdHandler.run_command(path=self.__perf_test_path,
                                              command="git clone git@github.com:taosdata/TDengine.git")

            self.__cmdHandler.run_command(path=self.__db_install_path, command="git reset --hard HEAD")
            self.__cmdHandler.run_command(path=self.__db_install_path, command="git checkout -- .")
            self.__cmdHandler.run_command(path=self.__db_install_path, command="git checkout {0}".format(self.__branch))
            self.__cmdHandler.run_command(path=self.__db_install_path, command="git pull")
            self.__cmdHandler.run_command(path=self.__db_install_path,
                                   command="sed -i \':a;N;$!ba;s/\(.*\)OFF/\\1ON/\' {0}/cmake/cmake.options".format(
                                       self.__db_install_path))
            self.__cmdHandler.run_command(path=self.__db_install_path,
                                          command="mkdir -p {0}/debug".format(self.__db_install_path))
            self.__cmdHandler.run_command(path=self.__db_install_path,
                                          command="rm -rf {0}/debug/*".format(self.__db_install_path))

            self.__cmdHandler.run_command(path=self.__db_install_path + "/debug", command="cmake .. -DBUILD_TOOLS=true")

            # Run the Bash script using subprocess
            # self.__logger.info("run cmake.sh")
            # subprocess.run(['bash', "./cmake.sh"] + ["{0}/debug".format(self.__db_install_path)], check=True)

            self.__cmdHandler.run_command(path=self.__db_install_path + "/debug", command="make -j 4")
            self.__cmdHandler.run_command(path=self.__db_install_path + "/debug", command="make install")
            self.__cmdHandler.run_command(path=self.__db_install_path + "/debug", command="systemctl start taosd")

            self.__logger.info("TDengine start successfully.")
        except Exception as e:
            self.__logger.error(f"Error running Bash script: {e}")


if __name__ == "__main__":
    pass
