FROM python:2.7-alpine

ENV SONARQUBE_HOME = /sonarqube-scanner

RUN apk add --no-cache curl grep sed unzip openjdk8-jre git bind-tools gcc g++ make libffi-dev openssl-dev openjdk8
RUN apk add --update nodejs nodejs-npm
RUN curl --insecure -o ./sonarscanner.zip -L https://sonarsource.bintray.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-3.2.0.1227-linux.zip
RUN unzip sonarscanner.zip
RUN rm sonarscanner.zip
RUN pip install boto3 pycrypto requests trufflehog


ENV SONAR_RUNNER_HOME=/sonar-scanner-3.2.0.1227-linux
ENV PATH $PATH:/sonar-scanner-3.2.0.1227-linux/bin

RUN mkdir /sonarqube-scanner
COPY sonar-scanner.properties $SONAR_RUNNER_HOME/conf/sonar-scanner.properties
COPY api.py /sonarqube-scanner
COPY sonar-project.properties /sonarqube-scanner
RUN chmod 777 /sonar-scanner-3.2.0.1227-linux/bin/sonar-scanner
RUN sed -i 's/use_embedded_jre=true/use_embedded_jre=false/g' /sonar-scanner-3.2.0.1227-linux/bin/sonar-scanner
WORKDIR /sonarqube-scanner
RUN mkdir reports

CMD ["python", "sonarqube.py"]

