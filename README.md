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

__paramiko__ - for ssh connection to remote hosts, by `violet` clients.

__Flask__ - for RESTful API.

__APScheduler__ - as main scheduler to store all the jobs.

__rabbitpy__ - as RabbitMQ connection layer.

__rrdtool__ - to store inner service statistics(version >=1.6, thread-safe),
and __python-rrdtool__, binding to rrdtool, to manage rrd files.

__requests__ - is used for testing, and will be used for commandline utility.

__tornado__ - as a threaded web-server for RESTful API. It's _not_ instaled
by default.

## Motivation

First of all - improving my programming skills and self-development.

## Installation

All the requirements can be found in `requirements.txt` file.

_to be continued_

## API Reference

TOBEDONE

## Tests

`apitests.py` - tests API calls. Uses __requests__ to send HTTP requests.

_to be continued_


## Documentation

TOBEDONE

## License

LGPL
