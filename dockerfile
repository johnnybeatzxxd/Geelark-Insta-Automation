FROM appium/appium:latest

USER root

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_BREAK_SYSTEM_PACKAGES=1

WORKDIR /opt/app
COPY requirements.txt .

RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN uv pip install -r requirements.txt
RUN appium driver install uiautomator2

WORKDIR /app
CMD ["tail", "-f", "/dev/null"]
