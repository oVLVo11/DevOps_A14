# A14 E4 可重复工程环境

E4 将 A14 的 BuildChecker 服务放入可重复的 Linux 容器环境。当前仓库包含课程 A 组模板要求的服务骨架、固定基础镜像、依赖锁、资源限制、单元测试、冒烟测试、环境自检和密钥扫描。

## 一键运行

E4 必须在课程分配的 Ubuntu 服务器上运行。每名实际操作者在自己的学号目录独立克隆，并只设置仓库级 Git 身份：

```sh
mkdir -p ~/241880223 && cd ~/241880223
git clone https://github.com/oVLVo11/DevOps_A14.git buildchecker
cd buildchecker
git config --local user.name 241880223
git config --local user.email 1211667299@qq.com
git rev-parse HEAD
make all
```

`make all` 依次执行：

1. `make doctor`，生成 `env.json`；
2. `make build`，生成 `build.log`、`image.json`、`toolchain.lock`；
3. `make test`，生成 `test.log`，预期 `3 passed`；
4. `make smoke`，生成 `smoke.json`，预期程序输出 `1` 且跟踪到 `config.h`；
5. `make scan`，生成 `secret-scan.txt`，预期未发现问题。

每次命令生成新的 `work/<时间>/`。`work/` 默认不进入 Git；发布证据时只挑选与指定源码 SHA 对应的成功目录。

## 可重复性边界

- 基础镜像以 OCI digest 固定；
- Python 依赖通过带哈希的锁文件安装；
- apt 工具的实际版本记录在 `toolchain.lock`；
- Compose 固定 CPU、内存、进程数、无网络和 `SYS_PTRACE` 权限；
- 服务以 UID 10001 的普通用户运行；
- `.env`、Git 历史和镜像层均接受密钥扫描；
- E4 冒烟测试只证明环境链路可用，不等同于 BuildChecker 算法实现。完整原始 `strace -ff`、`make -p` 和 MD/RD 推断属于 E5。

## 验收条件

正式 E4 证据需要满足：

- 课程服务器的 `env.json.problems` 为空；
- 同一完整源码 SHA 上两次独立克隆均运行成功；
- 两次 `toolchain.lock` 一致；
- 两次 `test.log` 均为 `3 passed`；
- 两次 `smoke.json` 均为 `passed: true`，结论一致；
- 两次 `secret-scan.txt` 均未发现问题；
- 假 Key 测试能够报错，清理后再次扫描通过；
- 最终记录源码 SHA、证据目录和差异解释。

详见 [A14 E4交付说明](A14_E4交付说明.md)。
