FROM eclipse-temurin:21-jre-jammy AS java
FROM node:22-bookworm-slim AS node
FROM ghcr.io/astral-sh/uv:0.11.0 AS uv
FROM jenkins/inbound-agent:jdk21 AS inbound
FROM python:3.12-bookworm
COPY --from=java /opt/java/openjdk /opt/java/openjdk
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=uv /uv /usr/local/bin/uv
COPY --from=inbound /usr/share/jenkins/agent.jar /opt/agent.jar
ENV JAVA_HOME=/opt/java/openjdk PATH="/opt/java/openjdk/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && npx --yes playwright@1.63.0 install --with-deps chromium \
    && useradd --uid 1000 --create-home jenkins \
    && mkdir -p /home/jenkins/agent && chown -R 1000:1000 /home/jenkins
USER 1000:1000
WORKDIR /home/jenkins/agent
CMD ["sh", "-c", "until test -s /agent-config/secret; do sleep 3; done; exec java -jar /opt/agent.jar -url http://jenkins:8080 -name photohearth-ci -secret @/agent-config/secret -webSocket -workDir /home/jenkins/agent"]
