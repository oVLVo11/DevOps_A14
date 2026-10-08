# BuildChecker 服务镜像（A 组）。构建上下文是仓库根目录。
# 基础镜像按 digest 固定；系统工具与 Python 包版本写入 /opt/toolchain.lock；服务以普通用户运行。
ARG BASE_IMAGE=m.daocloud.io/docker.io/library/python@sha256:f82c96458eedc847b233e582eb31336f4954b39cae020b6dcf5b3ed0e5cbcd74
FROM ${BASE_IMAGE}

ENV LC_ALL=C.UTF-8 \
    TZ=UTC \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc make libc6-dev strace git \
 && rm -rf /var/lib/apt/lists/* \
 && dpkg-query -W -f='${Package}=${Version}\n' gcc make libc6-dev strace git > /opt/toolchain.lock \
 && echo "python3=$(python3 -c 'import platform; print(platform.python_version())')" >> /opt/toolchain.lock \
 && echo "arch=$(dpkg --print-architecture)" >> /opt/toolchain.lock

COPY requirements-dev.lock /tmp/requirements-dev.lock
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements-dev.lock \
 && pip freeze | sed 's/^/pip:/' >> /opt/toolchain.lock

RUN useradd --create-home --uid 10001 app && install -d -o app -g app /app
WORKDIR /app
COPY --chown=app:app services/buildchecker/ /app/
COPY --chown=app:app fixtures/ /app/fixtures/
USER app

CMD ["python3", "-m", "buildchecker", "--help"]
