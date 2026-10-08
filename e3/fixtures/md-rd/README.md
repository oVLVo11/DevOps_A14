# MD/RD人工基线

该样例同时包含一条缺失依赖和一条冗余依赖，范围限定为目标`main.o`及项目内头文件：

- `main.c`读取`config.h`，但`main.o`规则没有声明它，因此是MISSING；
- Makefile将`unused.h`声明为`main.o`前置依赖，但编译器不读取它，因此是REDUNDANT。

初次构建能成功且程序输出`1`，不能据此判断声明正确。只把`config.h`中的`VALUE`改为`2`后，普通增量构建仍输出旧值`1`；clean build输出`2`。只修改`unused.h`会触发无必要的重新编译。

`e3/scripts/run_a14_e3.py`会复制本目录后执行测试，不会修改原始样例。
