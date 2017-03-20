## Synopsis

The aim of the project is to create nagios-like monitoring tool, which can be
scaled easily, and uses SQL database to store configuration data and history,
and RRD database files to store statistics.

Scheduler sends checks to MQ, so load can be easily redistributed by
simply launching client on new nodes.

Initially web-client was also included here, but it took a lot of time to
manage it, so it was dropped in favor of RESTful API, which later can be
used to create any interface, including web-client. Initial version of
command-line tool for communication with API already available.

Project is written in Python, 2.x branch.

**Misc**

At current phase I'm jumping from one library/technology to another without any
remorse.

Naming is inspired by __Ephel Duath's Painter's Palette (2003)__.

## Dataflow

![alt tag](https://s15.postimg.org/cvgrjgv5n/ppalette.png "ppalette dataflow")

**Green arrows**
`red` service fetches information for each plugin and generates schedule
based on interval of execution. Every N seconds scheduler is generating
check requests, which are converted to json format and sent to RabbitMQ
service.

`violet` service, running on single or several nodes, is
fetching requests from the queue. Check jobs can be nagios checks,
some custom scripts for checking custom services, discovery requests
for subnets, etc. At the moment only nagios scripts and discoveries are
supported.

**Blue arrows**
`violet` performs checks on the hosts and collects outputs and exitcodes.
`violet` supports execution of commands via ssh (via internal ssh
wrapper). In case ssh is used - connection from `violet` nodes to the
hosts should be configured via public ssh keys.

**Magenta arrows**
Once `violet` finishes check - it sends results to RabbitMQ, in json
format. `grey` service is fetching result from result's queue, and
inserts the data into the database.

**Violet arrows**
`violet` instances collect different statistical information, like
throughput, amount of active(alive workers), etc. This information
is sent to RabbitMQ every N seconds (heartbeat interval is configurable
in `violet` configuration file). `grey` service fetches this information
from particular queue in RabbitMQ and inserts the data to RRD database
files (separate file for each `violet` instance).

**Cyan arrows**
`grey` service collects statistical data from database, like amount of
hosts, amount of pingable hosts, amount of services in ok/warning/error
state (to count overall health status of environment, for example), and
etc. This information is inserted into RRD database file with common
statistics every N seconds.

**Orange arrows**
`red` service contains __API__. It's possible to perform many operations on
DB (fetching/adding/editing/deleting hosts/plugins/suites/networks),
trigger automatic discovery tasks for hosts in specific subnets(tasks
are sent to RMQ and executed by violet instances), fetch statistics for
`violet` instances and common statistics from database, show connected and
active `violet` instances, show scheduler jobs.

**Brown arrow**
`ppadm` is command-line interface to API. It supports (or should support)
all the operations available in API.

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

## Documentation

TOBEDONE

## License

LGPL
