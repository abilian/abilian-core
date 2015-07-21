#!/bin/bash

# exit on error
set -e

cp -r /vagrant $HOME/src
tox

