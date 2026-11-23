# A14 项目：双源文件计数程序

本项目由 A14 从 E3 `e3/fixtures/commits/project` 演进。原项目计算三个编译期常量的和。A14 将其中一项拆到独立的 `helper.c`，并在 Makefile 增加独立编译规则和代码级测试。目标版本新增 `adjustment.h`，用于检验漏声明头文件时的增量构建行为。

在本目录运行 `make clean && make && ./app`。基线输出 `12`，目标输出 `15`。运行 `make test` 对照 `expected.txt`。目标版本的干净构建能通过，但 `main.o` 未声明新增头文件。

给 `main.o` 补上 `adjustment.h` 后，在隔离副本将 `ADJUSTMENT` 从 3 改为 6，保持已有产物并运行 `make`。应重新编译 `main.o`，输出 `18`。验收完毕丢弃副本。使用 Linux、GNU Make 和 GCC。
