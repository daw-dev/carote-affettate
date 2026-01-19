#!/bin/bash

if [ $# -ne 1 ]; then
  echo "usage: \`./connect.sh <device>\`"
  exit 1
fi

dev=$1

container=$(docker ps -qf "name=\\_$dev\\_")

if [ -z "$container" ]; then
  echo "device not found"
  exit 1
fi

docker exec -ti $container /bin/bash
