#!/bin/bash

konnect() {
  if [ $# -ne 1 ]; then
    echo "usage: \`konnect <device>\`"
    exit 1
  fi

  dev=$1

  container=$(docker ps -qf "name=^kathara\\_.+\\_$dev\\_.+$")

  if [ -z "$container" ]; then
    echo "device not found"
    exit 1
  fi

  docker exec -ti $container /bin/bash
}
