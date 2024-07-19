# Use an official Python runtime as a parent image
FROM ubuntu:22.04

COPY dockerinstall.sh .
RUN chmod +x dockerinstall.sh && ./dockerinstall.sh

COPY kubeinstall.sh .
RUN chmod +x kubeinstall.sh && ./kubeinstall.sh

# Set the working directory in the container to /app
WORKDIR /app

# Add the current directory contents into the container at /app
ADD . /app

# Install any needed packages specified in requirements.txt
RUN apt-get update &&  apt-get install python3-pip -y
