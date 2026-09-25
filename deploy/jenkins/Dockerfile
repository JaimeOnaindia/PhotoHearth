FROM jenkins/jenkins:2.568.3-jdk21
USER root
RUN mkdir /agent-config && chown 1000:1000 /agent-config
USER jenkins
RUN jenkins-plugin-cli --plugins workflow-aggregator git junit
COPY bootstrap.groovy /usr/share/jenkins/ref/init.groovy.d/bootstrap.groovy
