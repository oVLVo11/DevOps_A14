# C0/C1/C2连续提交项目

该目录由Git标签`a14-e3-c0`、`a14-e3-c1`和`a14-e3-c2`保存三个真实版本。不要用目录名冒充版本；以`e3/baseline.json`记录的完整commit SHA为准。

- C0：源码与Makefile声明一致，默认输出10；
- C1：源码新增`feature.h`，Makefile漏声明该头文件；
- C2：源码保持C1，只把`CFLAGS`改为`-O0 -DMODE=7`。
