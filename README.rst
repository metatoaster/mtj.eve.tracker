Introduction
============

A tracker for resource levels of various structures for the game `EVE
Online`_.

.. _EVE Online: http://www.eveonline.com/

The aim of this package is to provide a **correct** status reporting of
various elements associated with towers that a corporation may own
within the the game environment.  The status reporting includes fuel
levels, location and states.  Other attributes such as fuel levels with
the associated time until offline are to be calculated as accurately as
possible in order to match what players may find within the game
environment.  Tower asset tracking is also planned.  A simple web
service component is provided, which can either be used as default which
can be extended to be a full web application environment for web
browsers.

Status
------

Current, the aim is to provide *correctness*, not speed or memory
efficiency.  When comprehensive test coverage is done to address the
various variations and problems dealing with the EVE API, work will be
done to ensure correctness within a multiprocess environment, such as
using a full featured wsgi environment, along with improvements to
speed and memory consumption.
