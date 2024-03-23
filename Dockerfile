FROM python:3.10-bullseye
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 5001
CMD [ "streamlit","run","bitmex.py" ]