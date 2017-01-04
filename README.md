## Synopsis

The aim of the project is to create nagios-like monitoring tool, which can be
scaled easily, and uses SQL database to store configuration data and
statistics.

Scheduler sends checks to MQ, so load can be easily redistributed by
simply launching client on new nodes.

Initially web-client was also included here, but it took a lot of time to
manage it.

So it was dropped in favor of RESTful API, which later can be
used to create any interface, including command line tool and web-client.

Project is written in Python, 2.x branch.

**Misc**

At current phase I'm jumping from one library/technology to another without any
remorse.
Naming is inspired by Ephel Duath's Painter's Palette (2003).

## 3rd party tools

__SQLAlchemy__ - as interface to DB.

__Flask__ - for RESTful API.

__APScheduler__ - as main scheduler to store all the jobs.

__rabbitpy__ - as RabbitMQ connection layer.

__rrdtool__ - to store inner service statistics, and python-rrdtool, binding to
rrdtool, to manage rrd files.

__rabbitmqadmin.py__ - used for debugging and monitoring RabbitMQ.

__tornado__ - as a threaded web-server for RESTful API.

## Motivation

First of all - improving my programming skills and self-development.

## Installation

TOBEDONE

## API Reference

TOBEDONE

## Tests

TOBEDONE

## Documentation

TOBEDONE

## License

LGPL