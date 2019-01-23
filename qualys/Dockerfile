FROM python:2.7-alpine


WORKDIR /usr/src/app

RUN apk add --no-cache gcc g++
RUN pip install xmltodict boto3 requests
COPY qualys.py ./

CMD ["python", "qualys.py"]


