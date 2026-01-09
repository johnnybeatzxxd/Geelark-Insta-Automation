FROM appium/appium:latest

USER root
WORKDIR /app


# Install uv 
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_BREAK_SYSTEM_PACKAGES=1
# Install libraries
COPY requirements.txt .
RUN uv venv
RUN uv pip install -r requirements.txt
RUN appium driver install uiautomator2

CMD ["tail", "-f", "/dev/null"]
