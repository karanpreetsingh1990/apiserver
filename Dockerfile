FROM python:3.13

LABEL maintainer="karanpreetsingh1990@gmail.com"

# RUN apt-get update && apt-get install -y && apt-get install python3 unzip python3-pip -y

WORKDIR /apps

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY --exclude=*.csv * ./

RUN useradd -m apprunner

RUN chown apprunner /apps -R

RUN mkdir -p /apps/logs/

USER apprunner

ENTRYPOINT ["python", "apiServer.py"]

#CMD ["sleep","infinity"]
